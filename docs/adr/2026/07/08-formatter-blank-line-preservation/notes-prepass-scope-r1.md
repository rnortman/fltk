# Scope prepass — round 1 (final)

No findings.

## Checks performed

- Diff `ef8f727..5864ae1` vs design §2 Components A and B: `fmt_config.py` mutates
  `trivia_config` in place (Component A); `pyrt.count_whitespace_newlines` +
  `gsm2unparser.py` unconditional-loop rewrite (Component B/Python); `gsm2unparser_rs.py`
  exhaustive per-variant match + regenerated `crates/fegen-rust/src/unparser.rs`
  (Component B/Rust) — all present and match the design's cited line ranges and semantics.
- §5 test plan items 1-10 all present and pass: `TestTriviaConfigDirectiveOwnership` (1-3),
  parsed-config clobbering-order + custom-trivia rendering tests (4, 5a, 5b),
  `TestCountWhitespaceNewlines` (6), Rust parsed-config + generated-source pins (7, 8;
  implementer split 8 into two tests — mixed-variant and all-node-variant/gear-shape — both
  legitimately extending the cited existing tests), and the gear-demo pinned acceptance test
  plus idempotency (9, 10). Ran the full set (`fltk/lsp/test_gear_demo.py`,
  `test_fmt_config.py::TestTriviaConfigDirectiveOwnership`, `test_pyrt.py`, the new
  `test_unparser.py::test_preserve_blanks_*`, `tests/test_rust_unparser_generator.py`,
  `tests/test_fltkfmt_parity.py`) — all green. `cargo check` on the workspace also succeeds.
- `TODO(rule-preserve-blanks)`: `TODO.md` entry + code comments at
  `gsm2unparser.py:1170/:1355` and `gsm2unparser_rs.py:1566` match the design's deferred-gap
  callout, join key consistent.
- Design's "deliberately NOT changed" list confirmed by absence from the diff:
  `examples/gear/gear.fltkfmt`, `fltk/lsp/server.py`, `fltk/unparse/resolve_specs.py`, the
  trivia-rule branch, and the `preserve_blanks` branch-emission ladders are all untouched.
  No generated public symbol/signature changes (§4).
- One documented deviation in the log (`test_formatting_preserves_leading_comment` doesn't
  exist in the base tree, contrary to design/exploration's assumption; leading-comment
  assertion folded into the new blank-lines test instead) — reasonable, and verified true
  against `ef8f727`.
- Noted but not a finding: the design and exploration docs describe
  `test_formatting_preserves_blank_lines_between_items` as "already committed and failing"
  at specific line numbers, but `git show ef8f727:fltk/lsp/test_gear_demo.py` has no such
  test — it did not exist before this round. This is a staleness issue in the design/
  exploration docs (likely written against an uncommitted working-tree snapshot), not an
  implementation gap: the implementer created the test fresh, with content matching the
  design's described acceptance criteria, and the log honestly says "created" rather than
  claiming it pre-existed. No action needed for this round.
- No diff hunks found that lack design/log traceability; no undesigned scope creep.

All design items accounted for in the single-increment log; nothing missing, nothing
unauthorized.
