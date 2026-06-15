# Deep test review: regex-portability-lint

Commit reviewed: ba953c8

---

test-1: F1/F4/F5 over-admissions are unpinned in `test_regex_portability.py`

File: `tests/test_regex_portability.py`, `_NON_PORTABLE_PATTERNS` list and surrounding tests

The spike findings F1 (`\07` octal family), F4 (`a{2,1}` inverted bound), and F5 (`[z-a]` reversed range) are documented in `test_regex_grammar_adversarial.py` as known over-admissions — the grammar accepts these patterns but both engines reject them. `test_regex_portability.py` has no test referencing any of them. Because the portability check (`check_regex_portable`) passes straight through to the regex grammar, these patterns will return `None` (no issue found) even though they are non-portable. There is no test in the portability suite that pins this known-false-negative behavior — not even a "this is a known gap, returns None" assertion with an explanatory comment. `test_regex_grammar_adversarial.py` pins the grammar's ACCEPT verdict for these cases, but that module tests the raw grammar, not `check_regex_portable`. A consumer of the lint who looks only at `test_regex_portability.py` gets no signal that these constructs slip through.

Consequence: a future grammar fix that starts correctly rejecting `\07`/`{2,1}`/`[z-a]` will have no test to catch the improvement, and the existing tests give no documentation that the cases are known gaps. More importantly, a regression that widens the grammar further (e.g. accidentally starting to accept `\07` on a grammar edit) will also not be caught by this suite.

Fix: add three tests to `test_regex_portability.py` that call `check_regex_portable` on `"\07"`, `"a{2,1}"`, and `"[z-a]"`, assert the result is `None` (confirming the known gap), and add a comment linking to the F1/F4/F5 rationale in `test_regex_grammar_adversarial.py`. This pins current behavior without claiming it is correct, and means a future fix will produce a clear test failure that prompts updating the assertion.

---

test-2: Wrong pattern in `_PORTABLE_PATTERNS` for the 4-hex unicode escape case

File: `tests/test_regex_portability.py`, line 128

```python
r"A",  # 4-hex unicode escape
```

`r"A"` is the single-character string `"A"` (the letter). The comment says "4-hex unicode escape," but a 4-hex escape in a regex pattern is the 6-character string `A` (backslash, u, four hex digits). The test passes because `"A"` is a portable literal character — but it does not exercise the `\uHHHH` escape path at all. The actual 6-char form `"\\u0041"` is what the design lists as a must-accept case (design §4.1: "`\uHHHH` (4-hex)" is admitted), and `check_regex_portable("\\u0041")` does return `None` (confirmed by execution), so the grammar handles it correctly — but the test doesn't reach that code path.

Consequence: the `\uHHHH` grammar path is untested. A future grammar change that accidentally breaks 4-hex escape recognition would not be caught by `test_regex_portability.py`. The passing test creates a false impression of coverage.

Fix: replace `r"A"` with `"\\u0041"` (the 6-char backslash-u-four-hex-digit string) and optionally add a second case like `"\\u0041"` for a different digit sequence.

---

test-3: Offset pinning tests do not distinguish `error_tracker.longest_parse_len` from `result.pos`

File: `tests/test_regex_portability.py`, lines 248–266 (`test_posix_class_offset_is_sensible`, `test_lookahead_offset_is_sensible`)

The design (§5.2) explicitly commits to `error_tracker.longest_parse_len` as the offset source — not `result.pos` — and explains why they differ: for a short parse, `result.pos` is the parse tree's consumed length while `longest_parse_len` is the furthest terminal failure, which is deeper into the rejected tail and more useful. The tests in the "Offset pinning" section assert only:

- `result.offset > 0` for `[[:alpha:]]`
- `result.offset >= 0` for `(?=x)` (vacuous — `offset` is never negative in normal operation since `longest_parse_len` starts at `-1` but is `-1` only when no terminal fires)

Neither test verifies that the offset came from `error_tracker.longest_parse_len` rather than `result.pos`. For `[[:alpha:]]`, the two would diverge: the grammar matches `[` as the start of a char class, then stalls at the second `[` (POSIX open), so `result.pos` would be `0` (the whole char_class path fails, returning the prefix before the class) or `1` (the outer `[` was consumed), while `longest_parse_len` would be `2` (the parser pushed past `[:` before failing). A test that asserts `result.offset >= 2` for `[[:alpha:]]` (or more precisely, `result.offset > 1`) would distinguish the two sources. The current `result.offset > 0` threshold is too loose.

Consequence: the design's offset-source choice is unverified. An implementation that reports `result.pos` instead of `longest_parse_len` would pass all existing offset tests while giving users a less informative (and differently-sourced) offset in error messages. The design specifically called this out as something to pin.

Fix: add a test that asserts `result.offset >= 2` for `[[:alpha:]]` (the POSIX-class motivating case), with a comment explaining that `result.pos` would be `0` or `1` while `longest_parse_len` reaches inside the `[:` before failing. This makes the test falsifiable with respect to the two sources.

---

test-4: No positive-control round-trip test for the committed `regex_parser.py`

File: `tests/test_regex_portability.py` (absent)

Design §7 requires: "Positive-control round-trip for the committed validator parser: a test that pins the committed `regex_subset_parser.py` actually came from a clean `regex_subset.fltkg` — e.g. regenerate the parser into a temp dir and assert it matches the committed file, or (lighter) assert the committed parser re-parses the in-tree corpus and the admitted/excluded unit sets identically."

No such test exists in the diff. The design acknowledges the risk in §6: "The committed regex-subset parser drifting from its grammar" and says "It joins `make gencode`… the regen-confirm step in §7 catches drift." But `make gencode` is a manual step, not a test-suite gate. The whole-tree completeness test partially discharges this (a grammar drift that changes classification would surface there), but it only catches drift that changes observable outcomes on the committed grammars — it would miss a drift where the parser's rules changed in a way that doesn't affect any in-tree pattern.

Consequence: the committed `regex_parser.py` can drift silently from `regex.fltkg` if someone edits the grammar and commits without regenerating. The whole-tree test provides only partial coverage of this drift.

Fix: add a test that calls `check_regex_portable` on all entries in both `_PORTABLE_PATTERNS` and `_NON_PORTABLE_PATTERNS` from the unit-test lists and asserts the expected classification — this is cheap (no regen needed) and would catch grammar drift that changes any of the pinned cases. The regen-into-temp-dir check is a stronger alternative but requires `make gencode` to be available in the test environment.

---

test-5: Duplicate `\A` and `\z` entries in `_PORTABLE_PATTERNS`

File: `tests/test_regex_portability.py`, lines 89–90 and 124–125

`r"\A"` and `r"\z"` each appear twice in `_PORTABLE_PATTERNS` — once under `# Anchors` (lines 89–90) and again under `# Top-level anchor/control escapes` (lines 124–125). Parametrized tests will run these cases twice, giving the appearance of broader coverage without adding any new assertion.

Consequence: Minor. No false negative or false positive. A reader scanning the list may overestimate coverage, and a future deduplication may accidentally remove the wrong instance and eliminate the comment context. Not a regression risk.

Fix: remove the duplicate pair at lines 124–125 (keep the ones under `# Anchors` with their context). Alternatively, consolidate the two comment sections into one and keep both labels.
