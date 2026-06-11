Style note: concise, precise, complete, unambiguous. No padding.

## scope-1

- Disposition: Fixed
- Action: Replaced `("grammar", '"café" :=', FAIL)` with `("grammar", 'x := "café" ** ;', FAIL)` in `tests/test_rust_parser_parity_fegen.py` (line 72). The original entry errored at position 0 (before any multibyte content); the replacement errors at position 12, after the multibyte 'é' at position 9, so line/col and caret indexing must traverse the multibyte character.
- Severity assessment: Without this entry, a codepoint/byte indexing bug in the Rust error formatter that miscomputes line/col or caret position when multibyte text precedes the error would pass all tests silently.

## scope-2

- Disposition: Fixed
- Action: Added `("expr", "1+2+3 ", PARTIAL(5))` to `_CORPUS` in `tests/test_rust_parser_parity_fixture.py` (line 62). Outcome is PARTIAL(5), not SUCCESS: the fixture grammar's `expr` rule does not consume trailing whitespace when `capture_trivia=False`, so both backends correctly stop at pos 5.
- Severity assessment: Without this entry, a trailing-position-off-by-one regression in the Rust parser (returning pos=4 instead of pos=5) would not be caught.

## scope-3

- Disposition: Fixed
- Action: Reworked comparator self-tests in `tests/test_rust_parser_parity_fegen.py` and extracted `_assert_messages_equiv` from `assert_error_equiv` in `tests/parser_parity.py`. All ten required dimensions are now genuinely pinned:
  - **kind** (`test_assert_cst_equal_fails_kind_mismatch`): identifier vs rule node — kind check fires first. Pinned.
  - **span** (`test_assert_cst_equal_fails_span_mismatch`): same kind, different span lengths. Pinned.
  - **child-count** (`test_assert_cst_equal_fails_child_count_mismatch`): hand-built Grammar nodes share identical `Span(0,10)` so span check cannot fire first; length check is the discriminator. Pinned.
  - **label** (`test_assert_cst_equal_fails_label_mismatch`): same span/kind/length, one label stripped. Pinned.
  - **deep-child/recursion** (`test_assert_cst_equal_fails_deep_child_mismatch`): hand-built Grammar/Rule/Identifier nodes all share the same outer span (`Span(0,25)`); only the leaf Identifier span differs (end=5 vs end=6), so comparator must recurse to detect the mismatch. Pinned.
  - **species node-vs-span** (`test_assert_cst_equal_fails_species_node_vs_span`): Python has node child, Rust has span child. Pinned.
  - **species span-vs-node** (`test_assert_cst_equal_fails_species_span_vs_node`): Python has Span child, Rust has Identifier node child; same kind/span/child-count/labels so species check is the discriminator. Pinned.
  - **header** (`test_assert_error_equiv_fails_header_mismatch`): tests through `_assert_messages_equiv` with hand-built headers differing in line/col text; failure fires at header comparison, not at position check. Pinned.
  - **group order** (`test_assert_messages_equiv_fails_group_order`): tests through `_assert_messages_equiv` with reversed rule-group dict order; raises on key-list inequality. Pinned.
  - **token set** (`test_assert_messages_equiv_fails_token_set`): tests through `_assert_messages_equiv` with differing token sets per rule; raises on set inequality. Pinned.
- Severity assessment: Without these self-tests, a vacuous comparator (one that never recurses, never compares labels, or skips message-structure checks) would green the entire parity corpus silently.

## scope-4

- Disposition: Fixed
- Action: Added `("items", "", FAIL)` to `_CORPUS` in `tests/test_rust_parser_parity_fixture.py` (line 68).
- Severity assessment: Without this entry, a Rust generator bug that turns `+`-on-empty into a vacuous success would not be caught by the parity suite.
