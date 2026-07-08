# Deep test review — round 1 (base ef8f727..HEAD 5864ae1)

## Verification method

For each new test that claims to pin a defect, I reverted the relevant production file(s) to
their `ef8f727` version (or hand-patched the fix to reintroduce the bug) and re-ran the test to
confirm red→green. All of the following were confirmed to fail against the pre-fix code and pass
against the fix:

- `fltk/unparse/test_fmt_config.py::TestTriviaConfigDirectiveOwnership::test_preserve_blanks_before_trivia_preserve_survives`
- `fltk/unparse/test_fmt_config.py::TestTriviaConfigDirectiveOwnership::test_repeated_trivia_preserve_last_wins_preserve_blanks_survives`
- `fltk/unparse/test_unparser.py::test_preserve_blanks_parsed_config_clobbering_order_direct_span`
- `fltk/unparse/test_unparser.py::test_preserve_blanks_custom_trivia_node_whitespace_survives`
- `fltk/lsp/test_gear_demo.py::test_formatting_preserves_blank_lines_between_items`

`fltk/unparse/pyrt.py::count_whitespace_newlines` unit tests
(`fltk/unparse/test_pyrt.py::TestCountWhitespaceNewlines`) directly exercise the new helper with
span/whitespace-node/comment-node/empty-span inputs and pass; not vacuous.

`tests/test_rust_unparser_generator.py`'s three new tests assert on generated Rust source text
(exact match-arm bodies), consistent with this file's established pattern for pinning the Rust
backend without compiling it; the parsed-config test
(`test_non_trivia_rule_preserve_blanks_from_parsed_clobbering_config`) mirrors the Python
component-A test and pins that the fixed config layer reaches the Rust generator.

## Findings

### test-1: comment-terminator guard test doesn't actually discriminate the whitespace-only rule it claims to guard

`fltk/unparse/test_unparser.py:1232`
(`test_preserve_blanks_custom_trivia_comment_terminator_not_counted`).

The test's docstring says it "guards component B's whitespace-only rule" — i.e. it exists to
catch a regression where a node-typed trivia child's newlines get counted even when the node
holds non-whitespace (a comment). The test input is `"foo; // c\nbar;\n"`: a single line comment
in the gap, no source blank line, asserting `blank_count == 0`.

I hand-verified this assertion is satisfied by a **deliberately broken** implementation of
`count_whitespace_newlines` that removes the whitespace-only check entirely (i.e. counts a node
child's newlines unconditionally, exactly the bug component B fixes):

```
count_whitespace_newlines(child, terminals) -> text.count("\n")   # no is-whitespace guard at all
```

Running the test's own input against this broken helper still yields `blank_count == 0` and the
test still passes. Reason: the gap in this input contributes at most one trivia child with a
newline (the comment's `\n` terminator) — a single stray newline never reaches the `newline_count
>= 2` threshold that gates blank-line emission (`fltk/unparse/gsm2unparser.py:1176`-`1180`,
mirrored Rust `gsm2unparser_rs.py`). So the assertion is satisfied regardless of whether the
whitespace-only check exists; it happens to pass both for the correct implementation and for the
bug it's supposed to catch.

I confirmed the discriminating input exists: `"foo; // c1\n// c2\nbar;\n"` (two consecutive line
comments, still no source blank line) does distinguish them — against the broken helper it
renders with a spurious blank line (`blank_count == 1`, i.e. `'foo;\n\nbar;\n'`), against the
actual fixed code it correctly renders `blank_count == 0`. That's because two mis-counted comment
terminators sum to 2, crossing the threshold.

**Consequence:** a future regression that reintroduces exactly the bug this fix addresses (drop
the whitespace-only guard, or weaken it) would not be caught by this test, despite the test's
docstring and stated purpose claiming otherwise. Anyone reading green CI would believe the
whitespace-only rule is pinned when it isn't.

**Fix:** change the test input to something that actually crosses the `>= 2` threshold if the
whitespace-only check is dropped — e.g. two consecutive unpreserved line comments in the same gap
(`"foo; // c1\n// c2\nbar;\n"`), or a comment adjacent to a single real whitespace newline where
mis-counting the comment's terminator would push the total from 1 to 2. Assert `blank_count == 0`
on that input instead of (or in addition to) the current single-comment one.

## No other findings

- Component A tests (`TestTriviaConfigDirectiveOwnership`, the parsed-clobbering-order rendering
  test, the Rust parsed-config test) are precise, minimal, and confirmed red-before/green-after.
- Component B's positive case (`test_preserve_blanks_custom_trivia_node_whitespace_survives`) is
  confirmed red-before/green-after and asserts real rendered output, not just "didn't throw."
- The new `pyrt.count_whitespace_newlines` unit tests cover all four semantic branches (span,
  whitespace-only node, comment node, empty-span node) with direct assertions on the function's
  return value.
- The gear-demo integration test asserts on rendered output content (blank lines before four
  specific markers, leading comment preserved), not just success/failure, and is confirmed to
  fail pre-fix.
- Existing `preserve_blanks`/idempotency/parity test suites are unaffected and still pass; no
  existing test needed updating since component A/B only change behavior for inputs
  (clobbering-order config text, node-wrapped trivia whitespace) that had no prior coverage.
