# Adversarial validation: `error-msg-escape` TODO

Concise. No fluff. All claims anchored to file:line.

---

## Claim 1: Rust `format_error_message` embeds raw line text unescaped

**TRUE.**

`crates/fltk-parser-core/src/errors.rs:121-141` — `format_error_message` calls
`terminals.pos_to_line_col(tracker.longest_parse_len)`, extracts `lc.line_span.text()`, then
embeds it directly in the format string at line 136:

```rust
let mut result = format!(
    "Syntax error at line {} col {}:\n{}\n{}^\nExpected:\n",
    line + 1,
    col + 1,
    line_text,   // ← raw, no escaping
    spaces
);
```

`line_text` is whatever bytes appear between the two nearest newlines in the input. No C0
control filtering, no ESC stripping, no `\r` removal. The doc comment at lines 86-92 records
this explicitly and names the `TODO(error-msg-escape)` slug.

---

## Claim 2: Python `format_error_message` matches byte-for-byte

**SUBSTANTIALLY TRUE, with one known deterministic divergence in rule-ordering.**

`fltk/fegen/pyrt/errors.py:52-71` — Python's implementation:

```python
result = (
    f"Syntax error at line {error_linecol.line + 1} col {error_linecol.col + 1}:\n"
    f"{terminals.terminals[error_linecol.line_span.start : error_linecol.line_span.end]}\n"
    f"{' ' * error_linecol.col}^\n"
    f"Expected:\n"
)
```

Line 60 slices `terminals.terminals[line_span.start:line_span.end]` and embeds it raw — same
unescaped insertion. No escaping of C0 controls. The `line_text` exposure is identical on both
sides.

**Known non-byte-for-byte divergence (unrelated to this TODO):** Python uses
`defaultdict(set)` at line 64, making within-rule token iteration hash-nondeterministic. The
Rust implementation uses first-occurrence order (errors.rs:148-161). The parity comparator
explicitly accounts for this (see Claim 3 below).

**`col = -1` corner case:** Python's `' ' * error_linecol.col` produces `''` when `col == -1`
(Python silently treats negative repeat as 0). Rust's `" ".repeat(col.max(0_i64) as usize)` at
errors.rs:134 matches this: `(-1_i64).max(0) == 0`. This is not a divergence.

---

## Claim 3: Phase 3 parity comparator location and what it compares

**TRUE. The comparator is `tests/parser_parity.py`.**

Key functions:

- `_parse_error_message` (parser_parity.py:45-87): splits an error message into
  `(header_lines: list[str], rule_sections: dict[str, set[str]])`. Header lines are everything
  before the first `  From rule "..."` line. Rule sections map rule-name lines to token-line
  sets.
- `_assert_messages_equiv` (parser_parity.py:99-116): asserts `py_header == rust_header`
  byte-equal (line 107), then `list(py_rules.keys()) == list(rust_rules.keys())` (order-sensitive,
  line 109), then `py_rules[r] == rust_rules[r]` per-rule as a set comparison (line 114,
  unordered).
- `assert_error_equiv` (parser_parity.py:119-148): called from `run_parity_corpus_entry`
  (line 192) when a FAIL outcome is expected; calls `_assert_messages_equiv` after comparing
  error positions.

**The header lines are compared byte-equal (line 107).** The header contains:

```
Syntax error at line N col M:\n
<line_text>\n
<spaces>^\n
Expected:
```

`line_text` is in the header section. If Python and Rust both embed the same raw bytes from
input (which they do), the header comparison will pass for any input including those with
embedded control characters. A fix that escapes `line_text` differently on one side without
the other would break `py_header == rust_header` at line 107.

---

## Claim 4: "Cannot be fixed unilaterally" — is this real?

**TRUE.**

The comparator's `py_header == rust_header` check at parser_parity.py:107 is a `list`
comparison (list of strings). The header lines are produced by `splitlines()` (line 61),
which splits on `\n`. For any input that contains a control character in its failing line
(e.g., ESC `\x1b`, `\r`, `\x01`), Python's header line 2 would be
`"...raw-line-with-ESC..."` and Rust's would be the same raw bytes. If only Rust escaped, Rust
would produce `"...\\x1b..."` while Python produces `"...\x1b..."` — the `==` at line 107
fails.

Test suites that would break: `test_rust_parser_parity_fegen.py` and
`test_rust_parser_parity_fixture.py`, any corpus entry that hits a FAIL outcome where the
failing line contains a non-ASCII or C0 control character. The existing FAIL corpus entries
use ASCII-safe input, so no current test would fail on the *current* corpus — but the
comparator itself would enforce symmetry if such input were added.

---

## Claim 5: Fix shape — "escape C0 controls (except `\n`/`\t`) in `line_text`, then update the comparator"

**Factually accurate description of what would need to happen; no hidden blockers from the
code side.**

Mechanically:
1. Both `format_error_message` implementations must apply the same escaping to `line_text`
   before building the string.
2. The comparator's `py_header == rust_header` check at parser_parity.py:107 can stay as-is
   if both sides apply identical escaping — the strings would still be equal. No change to the
   comparator structure is needed *unless* the escaping function itself has a language-dependent
   representation (e.g., Rust `\x1b` vs Python `\x1b` in display — which would not differ if
   both emit the same escaped string).
3. The golden test at errors.rs:311 (`format_error_message_basic`) pins `line_text = "hello
   worl"` (ASCII-clean); it would not need changing. No existing test uses control characters
   in the failing line.

**Layer question: is the formatter the right layer?**

The code does not provide an answer — no downstream consumer in-tree surfaces parse errors to
a terminal or log. `fltk/plumbing.py` and `fltk/unparse_cli.py` call `format_error_message`
indirectly via `error_tracker`; neither applies additional escaping before printing. The
security note at errors.rs:86-92 treats formatter-level escaping as the designated fix point.
There is no in-tree display layer that could alternatively own the escaping.

---

## Claim 6: "matches Python's `format_error_message` byte-for-byte"

**PARTIALLY true.** The `line_text` embedding is identical. The `col = -1` negative-repeat
behavior is matched. The format template structure is byte-for-byte identical for the header
lines. The **only** known divergence is within-rule token ordering in the `Expected:` section,
which is **not** in the header lines and is already handled by the set-comparison in the
comparator. The phrase "byte-for-byte" in the TODO is therefore accurate for the header section
(where the security-relevant `line_text` lives) and acceptable as a characterization of the
overall format intent.

---

## Summary of open factual questions

None. All claims in the TODO are verified against code with the minor clarification that
"byte-for-byte" applies to the header section (which is what matters for the parity constraint),
not the entire message (where hash-nondeterministic token ordering exists but is already handled
by the comparator).
