# Dispositions — regex-grammar-spike respond round 1 + rework

Commit reviewed: 88282829. Fixes committed at: 7721a40. Rework fixes committed at: (see HEAD).

---

## correctness-1

**Disposition:** Fixed

**Action:** Added two new F6 ACCEPT/FINDING cases (`[a-z&&b]`, `[a&&b]`) in the set-operation section of `tests/test_regex_grammar_adversarial.py:162-183` with `skip_re_check=True`. Updated the module docstring (`tests/test_regex_grammar_adversarial.py:30-31`) to add F6 to the findings inventory and soften the "fails CLOSED on every other divergent shape" claim to "fails CLOSED on most divergent shapes (see F6 for the one exception)". Confirmed via `classify_pattern('[a-z&&b]')` → `True` against the live parser.

**Severity assessment:** Real over-admission in the dangerous direction. The grammar's primary purpose (once adopted by the lint) is to fail-closed on non-portable constructs; silently admitting `&&` set-intersection look-alikes while claiming to close that door defeats the spike's go/no-go deliverable.

---

## correctness-2

**Disposition:** Fixed

**Action:** Added `[\07]` (ACCEPT/FINDING, F1-in-class) and `[\0]` (ACCEPT, benign baseline) cases after the in-class escape section at `tests/test_regex_grammar_adversarial.py:563-578`. Confirmed via `classify_pattern('[\\07]')` → `True`. The rationale explains that `class_escape_body → char_escape → control_escape` is the same shared path as the top-level F1 gap, so the blast radius is in-class as well.

**Severity assessment:** The F1 finding already documented the gap but understated its reach. An author writing `[\07]` would get the same Python/Rust divergence as top-level `\07`, unflagged by the test suite. Pins it so the documented finding is complete.

---

## correctness-3

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** The reviewer correctly notes there is no guard against same-pattern, different-expected duplicate rows. However the finding itself states "no current bug" and "verified: the only duplicate pattern is `(?i)` and both rows agree (ACCEPT)." A structural assertion would cost code complexity with zero current bug-fixing benefit. The finding is a latent fragility in a stable, reviewed table, not an active defect.

**Rationale (Won't-Do):** Adding a module-level dedup assertion purely to guard a latent edge case that does not exist today and would only surface on a future contributor's copy-paste error is overhead without payoff at this scope. If the table grows significantly, revisit.

---

## errhandling-1

**Disposition:** Fixed

**Action:** Broadened the except clause in `fltk/fegen/regex_corpus.py:107` from `(ValueError, FileNotFoundError)` to `(ValueError, OSError)`. `OSError` is the base class for `FileNotFoundError`, `PermissionError`, and other I/O failures from `Path.open()`. Added a comment explaining the coverage. `UnicodeDecodeError` is a subclass of `ValueError` and was already caught.

**Severity assessment:** Without the fix, a `PermissionError` on a grammar the developer cannot read would propagate as a raw traceback instead of the structured `"error: could not parse grammar …"` message. Diagnosability impact only (not a silent failure), but the structured message is the intended user experience.

---

## errhandling-2

**Disposition:** Fixed

**Action:** Wrapped the two module-level `_corpus_cases(...)` calls in `tests/test_regex_grammar_corpus.py:57-63` with a `try/except Exception` that re-raises as `pytest.UsageError` with a message naming both grammar files and the remediation step (`maturin develop`). Removed the TODO comment from the test file and the `corpus-test-collection-error-context` entry from `TODO.md`.

**Severity assessment:** A missing grammar file or un-built `fltk._native` now produces a structured `pytest.UsageError` with a maturin develop hint instead of a raw traceback. Low severity (visible failure, not silent), but the fix is a 5-line `try/except` that directly applies the cheap alternative both reviewers offered.

---

## security-1

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** Stack exhaustion on a deeply-nested adversarial pattern is bounded to a single invocation crash with no data loss or privilege escalation. The reviewer's own assessment is "Flagged for awareness only" and "none required for a spike-scoped local tool." Catching `RecursionError` in `run_cli` and routing it through the error message would actively mask a structural limit of the FLTK parser runtime that applies to every grammar, not just this one — hardening it here without hardening the shared runtime would give false confidence.

**Rationale (Won't-Do):** The behavior (stack exhaustion on deep nesting) is inherent to the FLTK-generated recursive-descent parser runtime (`fltk/fegen/pyrt/memo.py`) and is present for every grammar, not introduced by this spike. Hardening only the `run_cli` entry point without addressing the root in the shared runtime would be misleading. The asset at risk (one CLI invocation) and the impact (crash, no code execution or data disclosure) do not warrant the change in a local dev tool.

---

## test-1

**Disposition:** Fixed

**Action:** Replaced `r"A"` with `"\\u0041"` (the explicit 6-char string) at `tests/test_regex_grammar_adversarial.py:281`. Added a second case `"\\u00E9"` (hex with letter digit) to confirm the hex-digit class admits letter digits. Confirmed: `r"A"` evaluates to single-char `'A'` in Python 3.12+ (the `\u` sequence is processed as a unicode escape even inside raw strings in newer CPython versions).

**Severity assessment:** The `\uHHHH` 4-hex unicode escape was completely untested. A grammar regression that broke `unicode_escape` for the lowercase-`u` 4-hex form would not be caught by any test, directly violating a design §4.2 coverage obligation.

---

## test-2

**Disposition:** Fixed

**Action:** Added `test_cli_exit2_on_wrong_arg_count` and `test_cli_exit2_on_nonexistent_file` to `tests/test_regex_grammar_corpus.py:180-190`. Both call `run_cli` directly and assert exit code 2. All tests pass.

**Severity assessment:** The exit-2 branches (usage error and file-not-found) are the paths most likely to be silently broken by a refactor. Since `run_cli` is the developer's clockwork-verification tool, silent exit-0 on argument errors is a high-stakes false negative.

---

## test-3

**Disposition:** Fixed

**Action:** Added `test_cli_exit1_on_rejected_pattern` to `tests/test_regex_grammar_corpus.py:193-207`, using `tmp_path` fixture to create a minimal grammar containing `/(?=x)/` (a lookahead, rejected by `regex.fltkg`). Asserts `run_cli(...)` returns exit code 1. All tests pass.

**Severity assessment:** The `any_rejected` flag and exit-1 branch were completely untested. A regression where `run_cli` printed REJECT output but returned 0 would give a developer a false all-clear when running the ad-hoc clockwork verification.

---

## test-4

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** The reviewer correctly identifies that the six named risk-point pin tests duplicate the parametric sweep. However, the reviewer also states "no real behavior is left unchecked" and "the named pins' documentation value likely outweighs the noise." These are intentional, documented pins with explaining comments — removing them would lose the per-pattern-named failure messages that make a regression immediately actionable. The "noise" (two failures instead of one) is acceptable.

**Rationale (Won't-Do):** The pins serve a documentation-by-test function, not a pure coverage function. The design (§3.3) explicitly calls for pinning specific risk points with explaining comments "so a future grammar edit that breaks one fails loudly." Removing pins that exist by design to make specific failures named and actionable would actively harm the test suite's debuggability.

---

## reuse-1

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** `classify_pattern` duplicates the acceptance predicate from `parse_text`. The divergence risk is real but managed: the docstring now correctly states the motivation (allow callers to import only `regex_corpus` without pulling `fltk.plumbing`'s codegen imports), and the implementation is a one-liner that can be kept in sync trivially. The plumbing import at module top does not invalidate the per-function justification because `collect_regexes`/`run_cli` need it, not `classify_pattern`.

**Rationale (Won't-Do):** The duplicated predicate is 2 lines and is pinned by 185 tests that would catch any drift. Forcing a `parse_text` import into `classify_pattern` would couple the fast-path oracle to the full plumbing stack unnecessarily. The existing comment (updated by quality-1 fix) correctly explains the rationale.

---

## reuse-2

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** The two `parse_grammar_file` implementations (`genparser.py` vs `plumbing.py`) are pre-existing duplication that predates this spike. `regex_corpus.py` choosing the `plumbing` version is consistent with the test infrastructure's existing choice and does not introduce new divergence. Consolidating the two is a separate refactor with no bearing on this spike's correctness.

**Rationale (Won't-Do):** Pre-existing duplication; no new divergence introduced by this diff. Consolidation is out of scope for a validation spike and would require changing callers in the genparser pipeline.

---

## quality-1

**Disposition:** Fixed

**Action:** Updated `classify_pattern`'s docstring in `fltk/fegen/regex_corpus.py:70-74` to remove the stale "avoid importing the full plumbing stack" justification (which was rendered false by the module-level `parse_grammar_file` import) and replaced with an accurate description of the actual benefit (callers who only need classify_pattern can import just this module without pulling the full plumbing stack's codegen imports).

**Severity assessment:** Stale justification misleads future maintainers. No behavior impact.

---

## quality-2

**Disposition:** TODO(gsm-for-each-item-public)

**Action:** Added `# TODO(gsm-for-each-item-public)` comment at `fltk/fegen/regex_corpus.py:58` (the `gsm._for_each_item` call site) and a corresponding entry in `TODO.md`. No code change.

**Severity assessment:** Calling a private function cross-module creates a silent breakage risk (mypy/pyright won't flag it). However, promoting `_for_each_item` to public touches `gsm.py` and may have broader implications for GSM API surface — a deliberate decision for the owner of that module, not a respond-round patch.

---

## quality-3

**Disposition:** Fixed

**Action:** Replaced `assert len(patterns) == 12` with a frozenset equality assertion in `test_regex_fltkg_self_referential` (`tests/test_regex_grammar_corpus.py`). The expected set captures all 12 distinct patterns with inline comments naming each one (metachar_char, hex2, hex4, hex8, octal_digits, etc.). A failure now names the added/removed pattern. Removed the TODO comment from the test file and the `corpus-test-count-to-set` entry from `TODO.md`.

**Severity assessment:** The magic-number count was fragile and uninformative on failure. The frozenset fix is mechanical (the 12 patterns are already enumerated by the corpus CLI) and directly addresses the named consequence.

---

## quality-4

**Disposition:** Fixed

**Action:** Renamed `_run_cli` → `run_cli` in `fltk/fegen/regex_corpus.py:91` and updated the `__main__` call site. Updated the import in `tests/test_regex_grammar_corpus.py:23` and all call sites. The function's behavior is already externally documented (CLI command in `design.md` and module docstring), so there is no encapsulation rationale for the leading underscore.

**Severity assessment:** Importing a private symbol into a test makes refactoring brittle. Low severity but clean to fix.

---

## quality-5

**Disposition:** Fixed

**Action:** Combined with errhandling-2. See errhandling-2 — both are resolved by the same `try/except pytest.UsageError` wrapper at `tests/test_regex_grammar_corpus.py:57-63`.

---

## efficiency-1

**Disposition:** Fixed

**Action:** `test_regex_fltkg_self_referential` in `tests/test_regex_grammar_corpus.py:207` now derives its pattern list as `[p for p, _ in _REGEX_CORPUS]` instead of calling `parse_grammar_file(_REGEX_FLTKG)` and `collect_regexes(grammar)` again. This eliminates the redundant third full meta-parse of `regex.fltkg` per test run. Also removed the now-unused `parse_grammar_file` call from that function (the import is still used by `_corpus_cases`).

**Severity assessment:** Redundant parse work on every CI run. Bounded cost, but easily fixed by reusing the already-computed result.

---

## efficiency-2

**Disposition:** Won't-Do

**Action:** No change.

**Severity assessment:** The reviewer's own assessment is "None warranted. Listed so the reviewer record is complete; the cost is negligible and the readability of separate `_IDS`/`_UNPACKED` is worth more than the saved iteration." Agreed.

**Rationale (Won't-Do):** Trivial one-time module-load cost; reviewer explicitly recommended no change.
