# Quality review — regex-portability-lint

Commit reviewed: ba953c8. Base: 034252d.

---

## quality-1

**File:line** `tests/test_regex_portability.py:128`

**Issue** The entry `r"A"` labeled `# 4-hex unicode escape` in `_PORTABLE_PATTERNS` is not a 4-hex unicode escape — it is the plain letter `A`. Python raw strings (`r"..."`) suppress backslash interpretation for characters Python would otherwise treat as escape sequences, but they do not manufacture a backslash prefix. `r"A"` in Python evaluates to the single character `A` (U+0041), not to the six-character sequence `A` that is the regex `\uHHHH` escape construct.

Confirmed on disk: `od -c` of the file shows the bytes `r " A "` — no backslash, no `u`, no hex digits.

The intended test case is the pattern string `A`, which in Python source must be written `r"A"` (backslash, u, 0, 0, 4, 1 — six characters). As written the test exercises `A` as a portable plain literal, which passes for the wrong reason and leaves the `\uHHHH` path untested.

**Consequence** A regression in the regex grammar's `unicode_escape` production that silently broke 4-hex unicode escapes would go undetected. The `\UHHHHHHHH` (8-hex) case IS correctly tested at line 127, so there is asymmetric coverage between the two unicode escape forms that the commit intended to pair.

**Fix** Change line 128 from `r"A",  # 4-hex unicode escape` to `r"A",  # 4-hex unicode escape (\u + 4 hex digits)`.

---

## quality-2

**File:line** `tests/test_regex_portability.py:88-90, 123-125`

**Issue** `r"\A"` and `r"\z"` appear twice in `_PORTABLE_PATTERNS`:
- First occurrence: lines 88-90 (under `# Anchors`).
- Second occurrence: lines 123-125 (under `# Top-level anchor/control escapes`).

Each duplicated entry generates two pytest parametrize IDs for the same pattern, doubling the test run time for those cases and obscuring whether the intended coverage is present or just repeated.

**Consequence** Minor: doubled test execution for two cases, and the duplicate entries signal that the list was assembled additively without dedup review. If the list grows, future contributors will not know whether duplicates are intentional. The pattern also propagates: each "add more cases" pass appended to an existing section without scanning the full list.

**Fix** Remove the duplicate entries at lines 123-125 (the second occurrence). The `# Top-level anchor/control escapes` section can note that `\A` and `\z` are already covered above, or the anchors section can be reorganized to consolidate.

---

## quality-3

**File:line** `tests/test_regex_portability.py:440-451`

**Issue** The module-level parametrize call for `test_committed_rust_target_grammar_regex_is_portable` calls `_load_grammar_regexes(grammar_path)` eagerly in the decorator expression (lines 444-445, 449-450). If any grammar file cannot be loaded (missing Rust extension, missing file), this raises an unhandled exception at pytest collection time, producing an opaque traceback rather than a `pytest.UsageError`. The established pattern in the same test suite (`test_regex_grammar_corpus.py:57-65`) wraps the same operation in `try/except` and raises `pytest.UsageError` with a hint about `maturin develop`.

**Consequence** Users who run `pytest` without first building the Rust extension get a confusing import-time crash from `test_regex_portability.py` rather than the helpful message already present in `test_regex_grammar_corpus.py`. The inconsistency means the hint only appears for some tests, and the pattern will propagate to future parametrized tests that call `parse_grammar_file` at collection time.

**Fix** Wrap the `_load_grammar_regexes` calls in a `try/except` at module level, the same way `test_regex_grammar_corpus.py` does:

```python
try:
    _RUST_TARGET_PARAMETRIZE = [
        (str(gp), pattern)
        for gp in _RUST_PARSER_TARGET_GRAMMARS
        for pattern in _load_grammar_regexes(gp)
    ]
    _RUST_TARGET_IDS = [
        f"{gp.name}::{pattern[:40]}"
        for gp in _RUST_PARSER_TARGET_GRAMMARS
        for pattern in _load_grammar_regexes(gp)
    ]
except Exception as exc:
    raise pytest.UsageError(
        f"Could not load grammar files for portability check: {exc}\n"
        "Hint: run 'uv run --group dev maturin develop' to build the fltk._native extension."
    ) from exc
```

Then reference `_RUST_TARGET_PARAMETRIZE` and `_RUST_TARGET_IDS` in the `@pytest.mark.parametrize` call.

---

## quality-4

**File:line** `fltk/fegen/regex_portability.py:106`

**Issue** `f"unrecognised tail starting at {stopped!r}: "` applies `!r` (repr) to `stopped`, which is an integer. `repr(5)` is `'5'` — identical to `str(5)`. The `!r` serves no purpose on an integer (it would only matter for a string, where it adds quotes). The message reads `unrecognised tail starting at 5:` regardless. The probable intent was either to show the character at `stopped` (`pattern[stopped]`) or just to show the integer without `!r`.

**Consequence** Minor and self-contained, but the `!r` is confusing to future maintainers of the error message: they must think about whether it is intentional, realize it is a no-op on an integer, and then either leave the misleading formatting or fix it. Error message quality matters during incidents — a subtle formatting mistake in the offset line can mislead someone debugging a generation failure.

**Fix** Remove the `!r`: `f"unrecognised tail starting at {stopped}: "`.

---

## quality-5

**File:line** `fltk/fegen/regex_portability.py:95-99` and `fltk/fegen/gsm2parser_rs.py:793-794`

**Issue** The `offset` field of `RegexPortabilityIssue` can be `-1` (the `error_tracker` sentinel for "no terminal was reached"), and this is documented in the class docstring ("This is -1 if no terminal was reached"). However:

1. Inside `check_regex_portable`, the `detail` string normalizes this with `max(offset, 0)` before embedding the offset in the human-readable text — so the detail string never shows `-1`.
2. The caller in `gsm2parser_rs.py:794` embeds `issue.offset` directly: `f"(furthest progress: offset {issue.offset})"` — and can therefore print `offset -1` in the error message.
3. The same error message then appends `issue.detail`, which independently prints `offset 0` for the same hard-fail case.

This means a hard-fail error message reads: `...offset -1): the regex grammar could not start parsing at offset 0 (first unrecognised construct)...` — two contradictory offsets for the same position.

**Consequence** A grammar author who hits this path (pattern whose very first character is unrecognized) sees a confusing message with two different offset numbers. The inconsistency is likely to create a support question or cause the author to misidentify which offset to trust.

**Fix** Either (a) have `check_regex_portable` always store the clamped offset in `RegexPortabilityIssue.offset` (replace `offset` with `max(offset, 0)` or use `max(offset, 0)` in the constructor call at line 113), or (b) remove the redundant `(furthest progress: offset {issue.offset})` prefix in `gsm2parser_rs.py:794` since `issue.detail` already carries the offset. Option (a) is cleaner because it avoids repeating offset information at all.
