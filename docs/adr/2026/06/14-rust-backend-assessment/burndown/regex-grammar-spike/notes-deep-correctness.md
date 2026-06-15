# Deep correctness review — regex-grammar-spike

Commit reviewed: `88282829` (base `61df5ff`).

Scope reviewed: human-authored logic only — `fltk/fegen/regex.fltkg` (the grammar),
`fltk/fegen/regex_corpus.py` (extract/classify tool), `tests/test_regex_grammar_corpus.py`,
`tests/test_regex_grammar_adversarial.py`. The generated parser/CST modules
(`regex_parser.py`, `regex_cst*.py`, `regex_trivia_parser.py`) are machine output and out of
scope for hand-logic review.

All dispositions were validated against the live generated parser; the 177-case suite passes.
The tool logic (`collect_regexes` dedup/walk, `classify_pattern` oracle, parametrize unpacking,
ID handling, the count-12 pin) is correct — see "Verified clean" below. The findings concern the
adversarial suite's **coverage completeness vs. its own stated conclusions**, which is the spike's
core deliverable (it exists to enumerate over-admissions for the lint go/no-go), so a missed
over-admission that the suite claims does not exist is a correctness defect in the deliverable.

---

## correctness-1 — `&&` set-intersection look-alike is an UNPINNED over-admission; contradicts the suite's "set-op door closed" conclusion

- **File:** `tests/test_regex_grammar_adversarial.py:31` (module docstring claim) and
  `:128-142` (the "Set-operation look-alikes" section); grammar `fltk/fegen/regex.fltkg:223`
  (`class_char := /[^\\\]\[\-\n]/`).
- **What's wrong:** The grammar **accepts** `[a-z&&b]`, `[a&&b]`, `[ab&&cd]` (verified against
  the live parser — ACCEPT). `&` is not excluded from `class_char`, so `&&` parses as two
  ordinary literal class members. The adversarial suite's only `&&` case is `[a-z&&[^aeiou]]`
  (`:129-132`), which rejects **solely because of the inner `[`**, not because of the `&&` — its
  own rationale says so ("inner '[' has no class_char production"). No case exercises `&&`
  *without* a trailing `[`.
- **Why:** The module docstring asserts (`:30-31`) "The grammar fails CLOSED on every other
  divergent shape probed below" and (`:46`) "no over-rejections ... were found"; the grammar
  header (`regex.fltkg:10-13`) lists set ops `&&`/`--` as constructs that are "simply ABSENT and
  therefore rejected by construction." That is true for `--` (interior `-` is excluded from
  `class_char`, so `[\w--_]`/`[a--b]` reject — verified) but **false for `&&`**: `&` is an
  ordinary `class_char`, so the `&&` set-intersection door is open. Python `re` raises
  `FutureWarning: Possible set intersection` on `[a-z&&b]` (verified with warnings-as-errors) —
  the exact future-divergence signal the grammar header claims to fail closed on.
- **Consequence:** A grammar author can write `[a-z&&b]` and the portability recognizer (this
  grammar, once adopted by the lint) will pass it as portable, even though it is a flagged
  future-divergence construct on Python and a real set-intersection on Rust `regex-automata`
  (`[a-z&&b]` is intersection of `[a-z]` and `[b]`). This is the dangerous over-admission
  direction the spike exists to catch, and it is undocumented — the suite's "all over-admissions
  found" claim (F1–F5) is incomplete. The `--` door is genuinely closed; the `&&` door is not,
  and the suite asymmetrically tested only the form that happens to reject for an unrelated reason.
- **Suggested fix:** Add adversarial cases pinning `[a-z&&b]` / `[a&&b]` as ACCEPT with a
  `FINDING:` rationale (new F6, "`&&` set-intersection look-alike over-admitted; Python
  FutureWarning, Rust set-op divergence"), parallel to F4/F5. The grammar fix (excluding `&`
  from `class_char`, or rejecting a doubled `&`) is the downstream lint's call, but the finding
  must be recorded — leaving it silent defeats the spike's purpose. Also soften the docstring's
  "fails CLOSED on every other divergent shape" claim, which is currently false.

## correctness-2 — In-class octal `[\07]` (F1 family inside a class) is an UNPINNED over-admission

- **File:** `tests/test_regex_grammar_adversarial.py:283-299` (F1 octal family, top-level only);
  grammar `regex.fltkg:234-239,292` (`class_escape_body → char_escape → control_escape /[nrtfv0a]/`).
- **What's wrong:** The suite pins the F1 `\0N` octal over-admission only at **top level**
  (`\07`, `\00`, `\012`). The identical construct **inside a class** — `[\07]`, `[\0]`, `[\00]` —
  is also accepted by the grammar (verified ACCEPT) via `class_escape → class_escape_body →
  char_escape → control_escape` matching `\0`, then `0`/`7` as ordinary `class_char`. No case
  pins the in-class form.
- **Why:** F1's rationale (`:283`) states the gap is "the WHOLE family `\0N`" and the fix is
  "remove `\0` from control_escape." Because `control_escape` is shared by both the top-level
  (`escape_body`) and the class (`class_escape_body`) paths (`regex.fltkg:285-289,237-239`), the
  exact same over-admission exists in-class, where Python reads `[\07]` as a class containing
  octal `chr(7)` and Rust `regex-automata` rejects octal — the same Python-octal-vs-Rust-rejects
  divergence F1 documents. The suite's in-class escape section (`:514-553`) tests `[\b]`, `[\d]`,
  ranges, etc., but never the octal family.
- **Consequence:** The F1 finding under-states its own blast radius: the lint go/no-go reader is
  told the octal gap is a top-level concern, when it equally affects class bodies. A grammar
  author writing `[\07]` gets the same silent Python/Rust mis-parse, unflagged by the suite.
- **Suggested fix:** Add `[\07]` / `[\0]` cases as ACCEPT with an "F1 family (in-class)"
  `FINDING:` rationale, so the documented gap covers both reachable paths of `control_escape`.

## correctness-3 — Duplicate-pattern shadowing in ID generation is benign here but masks a latent contradiction-detection hole

- **File:** `tests/test_regex_grammar_adversarial.py:966` (`_IDS`) and the table at `:74-959`.
- **What's wrong:** `_IDS` maps `"[]"` → `"()"` (bracket→paren replacement) which collides with
  the literal `"()"` pattern's ID, and `"(?i)"` appears twice. pytest de-collides display IDs by
  suffixing, so no case is dropped (verified: 151 rows → 151 parametrized tests run). However,
  the table has **no guard against two rows with the same `pattern` but different `expected`** —
  a copy-paste contradiction would silently run both and one would fail only at execution, with
  no structural check that the table is internally consistent.
- **Why / Consequence:** Today this is clean — the only duplicate pattern is `"(?i)"` and both
  rows agree (ACCEPT), verified. So **no current bug**. Flagged as a latent fragility: the
  table is the spike's authoritative over-admission ledger, and a future edit introducing a
  contradictory duplicate would not be caught by any structural assertion (only by a runtime
  disposition mismatch on whichever row is wrong). This is a robustness note, not a defect.
- **Suggested fix (optional):** A one-line module-level assertion that
  `{p: e}` is single-valued across the table (no pattern maps to both ACCEPT and REJECT) would
  pin the ledger's internal consistency. Low priority.

---

## Verified clean (no findings)

- **`collect_regexes` walk + dedup** (`regex_corpus.py:37-64`): order-preserving dict dedup is
  correct; relies on `gsm._for_each_item` (`gsm.py:291-302`) which correctly recurses into
  `Sequence[Items]` sub-expressions. Produces exactly the 12 distinct terminals in `regex.fltkg`,
  matching the count-12 self-referential pin (`test_regex_grammar_corpus.py:192`). No off-by-one,
  no missed nesting.
- **`classify_pattern` oracle** (`regex_corpus.py:67-83`): `result is not None and result.pos ==
  len(terminals.terminals)` faithfully mirrors `parse_text`'s success predicate
  (`plumbing.py:323`). Correct accept = consume-to-end semantics; short parse → reject.
- **Parametrize unpacking** (`:969`): the optional-4th-element default-to-False handling is
  correct; all 151 rows unpack without index error.
- **`skip_re_check` cross-check logic** (`:998-1005`): ACCEPT-direction `re.compile` gate fires
  correctly and is suppressed exactly on the 8 documented over-admission rows (F1/F2/F3/F4/F5
  families); empty-string is correctly excluded from the cross-check. Verified: every non-skipped
  ACCEPT row compiles under Python `re`; every skipped row genuinely fails `re.compile`.
- **Full adversarial table (151 rows) and corpus suite (26 cases + pins):** every disposition
  reproduced against the live generated parser; suite passes (177 passed).
- **Whitespace / NO_WS property:** ` a`, `\ta`, ` *`, `a b` all ACCEPT and consume to end —
  confirms no `_trivia` stripping; the codepoint/byte UTF-8 cases (`é+`, `中*`,
  `a𝄞b?`, astral, NFD) all consume to `len(terminals)` in codepoints. No off-by-one in the
  codepoint position model exercised by these inputs.
