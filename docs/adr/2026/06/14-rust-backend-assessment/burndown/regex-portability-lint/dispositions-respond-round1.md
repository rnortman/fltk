# Dispositions — respond round 1

Commit reviewed: ba953c8. Fixes applied in: 6a43f9c.

---

## errhandling-1

- Disposition: Fixed
- Action: `fltk/fegen/regex_portability.py:95` — clamped `offset` to `max(parser.error_tracker.longest_parse_len, 0)` before constructing `RegexPortabilityIssue`; updated docstring to document that the field is always `>= 0`. Also updated `detail` string to use the already-clamped `offset` variable (removing the redundant `max(offset, 0)` calls). `gsm2parser_rs.py:794` is now consistent because `issue.offset` is never `-1`.
- Severity assessment: A grammar author whose pattern fails on the very first character would see `offset -1` from the ValueError and `offset 0` from the detail string — contradictory values that would cause confusion and potentially mask the real location of the problem.

## errhandling-2

- Disposition: Fixed
- Action: `tests/test_regex_portability.py:234` — changed `assert result.offset >= -1` to `assert result.offset >= 0`, consistent with the errhandling-1 fix that normalises the sentinel at construction.
- Severity assessment: Without this fix the test suite could not detect a regression where the sentinel `-1` leaked out; the guard would have allowed a regressing implementation to pass indefinitely.

## correctness-1

- Disposition: Fixed
- Action: `fltk/fegen/regex.fltkg:306` (old line 299) — changed `control_escape := value:/[nrtfv0a]/` to `value:/[nrtfva]/`. Regenerated and committed `regex_cst.py`, `regex_cst_protocol.py`, `regex_parser.py`, `regex_trivia_parser.py`. Added `\0`, `\07`, `[\0]` to `_NON_PORTABLE_PATTERNS` in `tests/test_regex_portability.py`. Updated adversarial test cases `\07`, `\00`, `\012`, `\0a`, `[\07]`, `[\0]` from ACCEPT (FINDING) to REJECT (fixed). Updated `tests/test_regex_grammar_corpus.py` expected terminal set from `[nrtfv0a]` to `[nrtfva]`. Updated F1 header in adversarial test.
- Severity assessment: A grammar author writing `rule := x:/\0/` (standard NUL match on Python) would receive a lint-clean pass, then a confusing Rust compile error citing "unsupported backreference" — the opposite of the lint's stated contract. This is a false negative against the lint's core invariant.

## correctness-2

- Disposition: Won't-Do
- Action: No change. `(?U)` remains admitted in `flag_chars`.
- Severity assessment: A grammar with `(?U)` passes the lint and compiles fine on the Rust backend but fails Python-backend compilation. This is a loud Python error, not a silent mis-parse — the consequence is a compile failure on the Python backend, not a divergent parse result.
- Rationale (Won't-Do): The design explicitly lists `(?U)` in §4.1 as admitted and the spike-outcome-gate.md F2 entry explicitly categorises it as "None. U is Rust-valid; it is non-portable only toward Python, and the lint is Rust-only by design (§5.3). This is intended behavior, not a gap." The docstring framing of "behaves identically on both engines" is an imprecision — the design's intent is "Rust-valid and not silently divergent", which `(?U)` satisfies. Removing `U` from `flag_chars` would over-reject legitimate Rust-only grammars. The correct resolution if the docstring framing matters is to update the docstring, but that is scope for `document-scope-boundary`, not a correctness fix here.

## correctness-3

- Disposition: Won't-Do
- Action: No change. Inverted bound `{m,n}` with m>n remains admitted.
- Severity assessment: A pattern like `a{3,1}` passes the lint, then fails the `all_regex_patterns_compile` Rust test. Both engines reject it — there is no silent semantic divergence, only a missed lint that is caught downstream.
- Rationale (Won't-Do): A context-free grammar provably cannot express the `min ≤ max` predicate. The design §6 and spike-outcome-gate.md F4 explicitly document this as an intrinsic limit of the recogniser approach and route these cases to the existing `all_regex_patterns_compile` gate. The lint's contract is "catch constructs that compile cleanly on both engines but match differently at runtime"; F4 fails at compile time on both engines and is therefore out of scope by design.

## correctness-4

- Disposition: Won't-Do
- Action: No change. Reversed range `[z-a]` (lo>hi) remains admitted.
- Severity assessment: Same shape as correctness-3: passes the lint, fails the Rust compile gate. Both engines reject it; no silent divergence.
- Rationale (Won't-Do): Same as correctness-3 — `lo ≤ hi` is a semantic predicate a CFG cannot express. Design §6 and spike-outcome-gate.md F5 explicitly document this as an intrinsic residual caught by the compile gate.

## security-1

- Disposition: Fixed
- Action: Same fix as correctness-1 — `\0` (and `\07`, etc.) now correctly rejected. See correctness-1.
- Severity assessment: Identical to correctness-1: a pattern that passes the lint then fails Rust compilation with a confusing "backreference" error, instead of the clear generation-time portability message the feature promises.

## test-1

- Disposition: Fixed
- Action: `tests/test_regex_portability.py` — added `test_f1_octal_escape_known_over_admission`, `test_f4_inverted_bound_known_over_admission`, `test_f5_reversed_class_range_known_over_admission`. The F1 test now asserts REJECT (the gap is fixed); F4/F5 assert ACCEPT (known gaps, CFG limit) with explanatory comments linking to spike rationale.
- Severity assessment: Without these tests, a future grammar change that accidentally widens coverage (admitting more non-portable constructs) or that fixes F4/F5 (returning the wrong verdict) would go undetected.

## test-2

- Disposition: Fixed
- Action: `tests/test_regex_portability.py:126` — changed `r"A"` to `r"A"` (the 6-character backslash-u-four-hex-digit string). Also added `\0`, `\07`, `[\0]` to `_NON_PORTABLE_PATTERNS` (correctness-1 byproduct).
- Severity assessment: The `unicode_escape` grammar path was entirely untested. A regression breaking 4-hex unicode escape recognition would have gone undetected while the test continued passing (the plain letter `A` is always portable).

## test-3

- Disposition: Fixed
- Action: `tests/test_regex_portability.py` — updated `test_posix_class_offset_is_sensible` to assert `result.offset >= 1` (not merely `> 0`) with updated docstring explaining that `longest_parse_len` is 1 (pushed past `[` at offset 0) while `result.pos` is 0 (char_class failed). The assertion is now falsifiable with respect to the two offset sources.
- Severity assessment: An implementation that substituted `result.pos` for `longest_parse_len` would pass the old `> 0` assertion for most cases but would return the less informative offset. The design specifically committed to `longest_parse_len` as the right source.

## test-4

- Disposition: TODO(regex-portability-roundtrip-test)
- Action: Added `TODO(regex-portability-roundtrip-test)` in `TODO.md` and a comment in `tests/test_regex_portability.py` before the whole-tree completeness check.
- Severity assessment: A committed `regex_parser.py` that has drifted from `regex.fltkg` (e.g., someone edits the grammar without regenerating) would go undetected if the drift does not change any in-tree corpus pattern's classification. The whole-tree test provides only partial coverage of this risk.

## test-5

- Disposition: Fixed
- Action: `tests/test_regex_portability.py` — removed duplicate `\A` and `\z` entries from the `# Top-level anchor/control escapes` section. Both are retained under `# Anchors`.
- Severity assessment: Minor — no false positive or negative. Doubled test execution for two cases and creates false coverage impression.

## reuse-1

- Disposition: Fixed
- Action: `fltk/fegen/regex_corpus.py:classify_pattern` now delegates to `check_regex_portable` from `regex_portability.py` (`return check_regex_portable(pattern) is None`), eliminating the duplicated `TerminalSource → RegexParser → apply__parse_regex → result-check` boilerplate. Removed the `TODO(regex-portability-check-reuse)` comment from `regex_portability.py:88` and its entry from `TODO.md`. Removed unused `terminalsrc` and `RegexParser` imports from `regex_corpus.py`; added `from fltk.fegen.regex_portability import check_regex_portable`.
- Severity assessment: Two locations previously expressed the same accept/reject predicate. A future parser-API change (e.g. start-rule rename, length-query shift) would have needed updating in two places; now there is one canonical site in `check_regex_portable`.

## quality-1

- Disposition: Fixed
- Action: Same as test-2 — the `r"A"` fix also closes this finding. See test-2.
- Severity assessment: The `\uHHHH` grammar path was untested; a regression would pass silently.

## quality-2

- Disposition: Fixed
- Action: Same as test-5 — removed duplicate entries. See test-5.
- Severity assessment: Minor.

## quality-3

- Disposition: Fixed
- Action: `tests/test_regex_portability.py` — wrapped `_load_grammar_regexes` calls in `try/except` at module level with a `pytest.UsageError` hint pointing at `maturin develop`. Matches the pattern in `test_regex_grammar_corpus.py`.
- Severity assessment: Users who run pytest without first building the Rust extension receive an opaque import-time traceback instead of the actionable hint already present in the sister test module. The inconsistency is user-hostile.

## quality-4

- Disposition: Fixed
- Action: `fltk/fegen/regex_portability.py:106` — changed `f"unrecognised tail starting at {stopped!r}: "` to `f"unrecognised tail starting at {stopped}: "` (removed `!r` from integer).
- Severity assessment: Minor. `repr(int)` is identical to `str(int)` — the `!r` is a no-op that misleads future maintainers into thinking it is intentional.

## quality-5

- Disposition: Fixed
- Action: Same as errhandling-1 — clamping the offset at construction removes the contradictory `-1` vs `0` pair from error messages. See errhandling-1.
- Severity assessment: Same as errhandling-1.

## efficiency-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:789` — gated the `check_regex_portable` call on `term.value not in self._regex_index` so each distinct pattern is checked exactly once, not once per occurrence.
- Severity assessment: A grammar that uses a complex regex in N rules pays N full parse-from-scratch costs for a result that is identical every time. In large downstream grammars with shared regex terms this is pure waste proportional to occurrences, not distinct patterns.

## efficiency-2

- Disposition: Fixed
- Action: `tests/test_regex_portability.py` — extracted `_RUST_TARGET_CASES` (built once) and derived `_RUST_TARGET_IDS` from it (`[f"{Path(gp).name}::{pat[:40]}" for gp, pat in _RUST_TARGET_CASES]`). Each grammar is now parsed once at collection time.
- Severity assessment: Every pytest collection over this module previously paid an extra full parse of three grammars (one of them the full FLTK self-hosting grammar). The overhead is small in absolute terms but is paid on every test run and every `-k`/collection-only invocation.
