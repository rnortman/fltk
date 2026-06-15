# Error-handling review — regex-grammar-spike

Commit reviewed: 88282829

---

errhandling-1

File: `fltk/fegen/regex_corpus.py:107-108`

**Broken path:** `_run_cli` catches `(ValueError, FileNotFoundError)` from `parse_grammar_file`, but `grammar_path.open()` inside `parse_grammar_file` (`plumbing.py:206`) can raise `PermissionError`, `UnicodeDecodeError` (non-UTF-8 file), or any other `OSError` subclass. None of these are in the caught tuple, so they propagate as unhandled exceptions with a full traceback instead of the clean `"error: could not parse grammar …"` message printed to stderr.

**Why:** `parse_grammar_file` documents only `ValueError` and `FileNotFoundError`, but the `Path.open()` call inside it can raise any `OSError`. The CLI is a user-facing tool (intended for ad-hoc runs against arbitrary `.fltkg` files on the developer's machine). A `PermissionError` on a file the user can't read, or a `UnicodeDecodeError` on a non-UTF-8 grammar, will crash with a raw Python traceback rather than a diagnostic message.

**Consequence:** On-call / developer sees a raw `UnicodeDecodeError` or `PermissionError` traceback with no context about which grammar file triggered it and no indication of what action to take. Silent-failure risk is low (it crashes visibly) but diagnosability is poor; the error message that was designed to be informative (`error: could not parse grammar …`) is bypassed.

**Fix:** Broaden the except clause to `except (ValueError, FileNotFoundError, OSError)` or `except Exception` (narrowed to the specific call site), so any I/O failure gets routed through the structured error message path. `UnicodeDecodeError` is a subclass of `ValueError`, so that family is already caught; `PermissionError` and other `OSError` subclasses are not.

---

errhandling-2

File: `tests/test_regex_grammar_corpus.py:1208-1209`

**Broken path:** `_FEGEN_CORPUS` and `_REGEX_CORPUS` are computed at **module import time** by calling `_corpus_cases()` which calls `parse_grammar_file()`. If the grammar file is missing, unreadable, or fails to parse during test collection, pytest gets a bare `ValueError` / `FileNotFoundError` / `OSError` traceback at collection time. The `grammar_path` that failed is present in the traceback frame but not in a surfaced error message; the test output reads as a collection error unrelated to any specific test case.

**Why:** Module-level `_corpus_cases` calls run before any test fixture or parametrize machinery can attach context. A file-not-found or parse-failure surfaces as `ERROR collecting tests/test_regex_grammar_corpus.py` with a raw exception, with no message naming the grammar file in a user-visible way.

**Consequence:** If an in-tree grammar path is wrong or the grammar file is absent (e.g., after a failed `make gencode`), the error message that an on-call sees is a raw traceback with no pointer to the actual problem. The two problematic cases (missing `fegen.fltkg` or missing generated `regex.fltkg`) are exactly the situations most likely to arise after a partial regeneration. The test failure is not silent — it fails loudly — but the message does not guide the engineer toward the fix.

**Fix:** Wrap the module-level corpus computation in a try/except that raises a `pytest.UsageError` or `RuntimeError` with a message naming the grammar path and the action needed (`make gencode` or check out the file), or defer the grammar loading to a fixture/function scope so pytest's `--tb` output can attach the file name as parametrize context.

---

No findings in `tests/test_regex_grammar_adversarial.py`. All error paths there either propagate through pytest (intentional — a test exception is a test failure) or are explicitly handled via `pytest.fail()` with full context including the pattern and rationale.

No findings in the Makefile change. The `gencode` target follows the existing pattern; failures in `uv run …` propagate as make errors with exit code, which is the correct behavior.
