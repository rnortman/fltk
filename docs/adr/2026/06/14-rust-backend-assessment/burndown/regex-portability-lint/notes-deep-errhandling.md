# Error-handling review — regex-portability-lint

Commit reviewed: ba953c8

---

## errhandling-1

**File:line:** `fltk/fegen/regex_portability.py:95` and `gsm2parser_rs.py:794`

**The broken error path:** `RegexPortabilityIssue.offset` is set to `parser.error_tracker.longest_parse_len` raw, which is `-1` when no terminal has ever fired (the initial sentinel in `ErrorTracker`). In the hard-fail branch (`result is None`, pattern not empty) the `detail` string guards against this with `max(offset, 0)` in the printed text, but `issue.offset` is still set to `-1` and that raw `-1` is what the caller in `gsm2parser_rs.py:794` embeds in the user-visible `ValueError` message: `"(furthest progress: offset -1)"`.

**Why:** `detail` normalises the display value (`max(offset, 0)`) but `offset` on the returned dataclass does not. The ValueError in `gsm2parser_rs.py` formats `issue.offset` directly, bypassing that guard. So a pattern whose very first character is unrecognised (hard fail on an empty `longest_parse_len`) produces a diagnostic saying `offset -1`, which is meaningless to an on-call reader and contradicts the `detail` field which says `offset 0`.

**Consequence:** The error message surfaced to the grammar author via `genparser gen-rust-parser` contains a contradictory pair of offset values (`offset -1` from `issue.offset` and `offset 0` from `issue.detail`). The pattern and the `detail` string are still present so the failure is diagnosable, but a reader seeing `-1` is likely to assume it is a sentinel meaning "unknown" and file a bug against the tool rather than investigate the pattern. No silent failure — the ValueError is raised and logged — but the diagnosis quality is degraded for the hardest-to-understand failure shape.

**What must change:** Either (a) normalise `offset` in `RegexPortabilityIssue` at construction time (`max(offset, 0)`) so the dataclass field never carries the sentinel value out of the module, or (b) guard the caller's format string in `gsm2parser_rs.py` the same way `detail` guards it (`max(issue.offset, 0)`). Option (a) is cleaner: the `offset` field's contract in the docstring says "codepoint offset of furthest progress" — a sentinel integer is not a codepoint offset and should not be exported.

---

## errhandling-2

**File:line:** `tests/test_regex_portability.py:235–236`

**The broken error path:** The non-portable-pattern tests assert `result.offset >= -1` — i.e. they explicitly pass the sentinel `-1` as a valid value. This means errhandling-1's sentinel-offset bug can never be caught by the test suite as written.

**Why:** The assertion was written permissively to avoid pinning the exact furthest-progress value as the grammar evolves. That is a reasonable concern for the numeric value itself, but lumping the sentinel `-1` into "valid" values means the one offset shape that signals "we never reached a terminal" is accepted by the test as correct. There is no test that asserts the hard-fail shape produces offset `>= 0`.

**Consequence:** errhandling-1 is latent and untested. A refactor that changes the `longest_parse_len` initialisation (e.g. to `None`) or that introduces a new hard-fail path would not be caught.

**What must change:** The offset assertion should be `result.offset >= 0` (not `>= -1`). If the grammar legitimately produces offset 0 for some hard-fail cases (e.g. a single-character unrecognised pattern like `\Z` where no terminal advanced past position 0), that is fine — 0 is a valid codepoint offset. The sentinel `-1` should never appear in the public `RegexPortabilityIssue.offset` field after errhandling-1 is fixed.
