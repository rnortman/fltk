Style note: concise, precise, complete, unambiguous. No padding.

## scope-1

**Missing — design §2.5 fegen corpus, multibyte error entry**

Design §2.5 specifies for the fegen corpus: "multibyte content preceding a syntax error (line/col + caret line parity over multibyte text)." The only multibyte corpus entry is `("raw_string", '"café"', SUCCESS)`. No FAIL entry with multibyte text preceding the error position exists.

Consequence: line/col rendering over multibyte input is not parity-tested on the failure path. A codepoint/byte indexing bug in the Rust error formatter that manifests only on multibyte text with a syntax error would pass all tests.

Suggested fix: add one corpus entry such as `("grammar", '"café" :=', FAIL)` — multibyte literal followed by a syntax error — to `_CORPUS` in `test_rust_parser_parity_fegen.py`.

---

## scope-2

**Missing — design §2.5 fixture corpus, trailing-character pair**

Design §2.5 specifies for the fixture corpus: "the trailing-character pair mapped onto the fixture grammar: the same input with and without a trailing whitespace character ('x+'-style — historically parsed one position short without trailing whitespace), each with its explicit SUCCESS/PARTIAL expectation; plus a SUCCESS entry ending in a non-whitespace terminal." No such paired entries appear in `test_rust_parser_parity_fixture.py` (no entry for `("expr", "1+2+3 ", SUCCESS)` / `("expr", "1+2+3", SUCCESS)` pair or equivalent). The `("expr", "1+2+3", SUCCESS)` entry alone does not satisfy the pairing requirement.

Consequence: the trailing-character bug class (parser returning `pos` one short when input ends without trailing whitespace) is not pinned in the fixture parity suite. That class of regression in the Rust parser would not be caught by these tests.

Suggested fix: add the pair `("expr", "1+2+3", SUCCESS)` (already present) + `("expr", "1+2+3 ", SUCCESS)` (new, with trailing space) to `_CORPUS` in `test_rust_parser_parity_fixture.py`. The non-whitespace trailing terminal is already covered by existing `("expr", "1+2+3", SUCCESS)`.

---

## scope-3

**Missing — design §4.4 comparator self-tests (under-specified)**

Design §4.4 requires: "assert_cst_equal fails on kind, span, label, child-count, deep-child, and species mismatches (a span child paired with a node child, in both directions)"; "assert_error_equiv fails on differing positions, headers, group order, and token sets — constructed from hand-built unequal inputs."

The diff contains three comparator self-tests: (1) passes-for-equal-nodes, (2) fails-for-different-inputs (different grammar strings — span difference, not individually targeting kind/label/child-count/species), (3) fails-for-different-positions only. Missing: self-tests that individually target kind mismatch, label mismatch, child-count mismatch, deep-child mismatch, species mismatch (span-vs-node in both directions), error-message header mismatch, rule group-order mismatch, and within-rule token-set mismatch.

Consequence: the comparator itself could have bugs (e.g., not recursing into children, not checking labels, not detecting species inversion) that would pass all three existing self-tests and silently green the parity corpus. The §4.4 "vacuous comparator" guard (§3, §4.4) is the mitigation; without individuated self-tests it is unenforceable.

Suggested fix: add targeted self-tests to `test_rust_parser_parity_fegen.py` constructing minimal hand-built nodes (via `fegen_rust_cst` CST constructors per §4.4) that differ on exactly the specified dimension, asserting each raises `AssertionError`. This is the largest gap among the three findings.

---

## scope-4

**Missing — design §2.5 fixture corpus, `items`/`+` empty-match case**

Design §2.5 maps `test_regression_empty_nary.py` to "* matching empty (SUCCESS), + matching empty (FAIL/PARTIAL), at start and mid-rule." The corpus covers `zero_items` (`*`) with empty input (SUCCESS) but has no entry for `items` (`+`) with empty input (which should be FAIL or PARTIAL at pos 0).

Consequence: the `+`-on-empty path is not parity-tested between backends. A Rust generator bug that turns `+`-empty into a vacuous success would not be caught.

Suggested fix: add `("items", "", FAIL)` to `_CORPUS` in `test_rust_parser_parity_fixture.py`.
