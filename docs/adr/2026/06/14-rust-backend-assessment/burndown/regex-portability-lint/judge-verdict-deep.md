# Judge verdict — deep review (regex-portability-lint)

Phase: deep. Base 034252d..HEAD 6a43f9c (fixes), reviewed against ba953c8.
Round 1.
Notes: 7 reviewer files; 22 findings.
Design: `burndown/regex-portability-lint/design.md`. Spike gate: `spike-outcome-gate.md`.

Ground-truth verification was run live against the HEAD-committed grammar
(`fltk/fegen/regex.fltkg`) and checker (`regex_portability.py`), plus the full
test module (131 passed).

## Added TODOs walk

### test-4 — TODO(regex-portability-roundtrip-test) at `tests/test_regex_portability.py:485` + TODO.md
Both pieces present (code comment + master-list entry, verified).
Q1 (worth doing): yes — the committed `regex_parser.py` can drift from `regex.fltkg`
if someone edits the grammar without regenerating; design §7 explicitly specifies a
positive-control round-trip test, and the whole-tree completeness test only catches
drift that reclassifies an already-pinned in-tree pattern.
Q2 (design/owner input required): yes, for the form that adds coverage. The *lighter*
oracle form the reviewer suggested ("run all `_PORTABLE_PATTERNS`/`_NON_PORTABLE_PATTERNS`
through the committed parser") is **already present** — `test_portable_pattern_returns_no_issue`
and `test_non_portable_pattern_returns_issue` (lines 159-160, 225-226) parametrize exactly
those lists against the committed parser. What remains genuinely uncovered is the
**regen-into-temp-dir byte-compare**, which depends on whether the generator/`make gencode`
should be invoked inside the test environment — an environmental tradeoff the design itself
flags as open (§7: "requires `make gencode` to be available in the test environment").
Assessment: residual work is the environment-dependent regen-compare, not the mechanical
oracle (already shipped). TODO acceptable.

### reuse-1 — TODO(regex-portability-check-reuse) at `fltk/fegen/regex_portability.py:88` + TODO.md
Both pieces present (code comment + master-list entry, verified).
Q1 (worth doing): yes — `check_regex_portable` (`regex_portability.py:92-96`) and
`classify_pattern` (`regex_corpus.py:80-83`) both do `TerminalSource → RegexParser →
apply__parse_regex(0) → result is not None and result.pos == len(...)`; a future parser-API
change (start-rule rename, length-query shift) touches two sites.
Q2 (design/owner input required): **NO.** The two functions are near-identical; the only
deltas are the length operand (`len(pattern)` vs `len(terminals.terminals)`, equivalent)
and the extra `error_tracker.longest_parse_len` read on the reject branch. Extracting a
shared lower-level helper that returns `(result, parser)` — `classify_pattern` returns the
bool, `check_regex_portable` adds the offset read — is mechanical, single-package, needs no
design cycle and no owner input. The reuse reviewer itself spells out the exact path
("`check_regex_portable` could call `classify_pattern` (or a shared lower-level helper)").
The responder's own note concedes "Currently low risk." This is not "design work required";
per the rubric it is **do-it-now**, and the TODO is being used to defer a mechanical
refactor rather than a genuine design/owner question.
Assessment: fails Q2 → do-now. Disposition wrong. (Severity: low-end reuse nit, pre-existing
duplication that this iteration *added one more copy to* rather than created; mitigates
escalation but does not change that the disposition should be Fixed, not TODO.)

## Other findings walk

### correctness-1 / security-1 — Fixed  [PROMPT VERIFY ITEM 1]
Claim: `control_escape := /[nrtfv0a]/` admits `\0` (and the whole `\0N` octal family) as
portable, but Rust `regex-automata` (octal off by default) rejects every bare `\0` form
as `UnsupportedBackreference`; Python `re` accepts `\0` as NUL. Consequence: a `/\0/`
grammar passes the lint then fails Rust compilation with a confusing "backreference" error
— a false negative against the lint's core invariant.
Diff at `regex.fltkg:306`: `control_escape := value:/[nrtfva]/` (the `0` is dropped); comment
rewritten to state `\0` is excluded and `\x00` is the portable NUL. Regenerated CST/parser
committed. `_NON_PORTABLE_PATTERNS` gains `\0`, `\07`, `[\0]`; adversarial F1 cases flipped
ACCEPT→REJECT with `skip_re_check`; corpus expected terminal set updated to `[nrtfva]`.
Live verification against HEAD grammar:
`\0`→offset 1, `\07`→1, `\00`→1, `\012`→1, `[\0]`→2, `[\07]`→2, `\0a`→1 — **all REJECTED**;
`\x00`, `[\x00]`→**PORTABLE** (NUL replacement intact).
Assessment: the `\0` false-negative is now actually flagged by the lint, grounded in the
removed grammar production (not hand-waving). Fix addresses the consequence; offset is
sensible. Accept.

### correctness-2 — Won't-Do (`(?U)` admitted)  [Won't-Do harm-check]
Claim: `flag_chars := /[imsU]+/` admits `(?U)`/`(?iU)`/`(?U:…)`; Python `re` rejects the
`U` flag (`unknown extension ?U`, verified live), Rust accepts it. The module docstring
frames the subset as "behaves identically on Python `re` and Rust `regex-automata`"
(`regex_portability.py:4`), which `(?U)` violates.
Rationale (Won't-Do): design §4.1 lists `U` as admitted by intent; spike-gate F2 explicitly
categorizes it "intended behavior, not a gap"; the lint is Rust-only by design (§5.3 —
verified: the only wiring is at the `gsm.Regex` branch of `gsm2parser_rs.py`, the Rust
generator). `(?U)` is Python-invalid/Rust-valid, the *inverse* direction from the silent
Python-works/Rust-breaks divergence the lint exists to close; a `(?U)` grammar is one an
author wrote deliberately for Rust and never worked on Python, so it is a loud Python compile
error, not silent divergence and not a regression of an existing working grammar. Removing
`U` would over-reject legitimate Rust-only grammars.
Assessment: argues genuine harm-avoidance (removing `U` actively breaks valid Rust-only
grammars), grounded in design + spike gate, not scope-punting. Both the correctness and
security reviewers themselves call the admission "internally consistent"/"intended by design"
and frame the residue as a docstring-vs-admission wording tension. The docstring imprecision
("behaves identically" vs the true admit-criterion "Rust-valid and not silently divergent")
is correctly routed to `document-scope-boundary` (the §5.4 doc-owning item). Accept Won't-Do.

### correctness-3 — Won't-Do (inverted bound `a{3,1}` admitted)
Claim: `bounded` is purely syntactic, no `min≤max` check; `a{3,1}` passes the lint.
Consequence: passes lint, fails Rust compile gate. Both engines reject (verified live:
Python `min repeat greater than max repeat`).
Rationale (Won't-Do): a context-free grammar provably cannot express the `min≤max` predicate;
design §6 and spike-gate F4 document this as an intrinsic recognizer limit routed to the
existing `all_regex_patterns_compile` Rust gate (confirmed present, `gsm2parser_rs.py:1031`).
No silent divergence — both engines reject at compile time.
Assessment: the only alternative to admitting the syntax is over-rejecting *all* bounded
quantifiers — active harm — and the inverted form is impossible to exclude in a CFG. Backstop
is real and the divergence class (both-reject) is outside the lint's silent-divergence
contract. Argues real harm-avoidance, not scope-punting. Accept.

### correctness-4 — Won't-Do (reversed range `[z-a]` admitted)
Claim/consequence: identical shape to correctness-3 — `class_range` syntactic only, `[z-a]`
admitted; both engines reject (verified live: Python `bad character range z-a`).
Rationale (Won't-Do): `lo≤hi` is the same CFG-inexpressible semantic predicate; design §6 /
spike-gate F5; same `all_regex_patterns_compile` backstop.
Assessment: same reasoning as correctness-3. Accept.

### errhandling-1 / quality-5 — Fixed  [PROMPT VERIFY ITEM 3]
Claim: `RegexPortabilityIssue.offset` was set to raw `error_tracker.longest_parse_len`, which
is the sentinel `-1` when no terminal fired; the caller at `gsm2parser_rs.py:794` embedded that
raw `-1` in the user-visible ValueError ("offset -1") while `detail` independently printed
"offset 0" — two contradictory offsets for the hardest-to-read failure shape.
Diff at `regex_portability.py:103`: `offset = max(parser.error_tracker.longest_parse_len, 0)`
clamped *at construction*; docstring updated to state the field is always `>= 0`; the redundant
`max(offset, 0)` calls in `detail` removed (now use the already-clamped `offset`). Caller
`gsm2parser_rs.py` now embeds `issue.offset`, which is never `-1`.
Live verification: hard-fail patterns `\1`→offset 1, `(?=x)`→offset 2; clamp path confirmed
(no negative offset exported). Assessment: contradictory `-1`/`0` pair resolved at the single
canonical site (the cleaner option the reviewer preferred). Accept.

### errhandling-2 — Fixed
Claim: the non-portable tests asserted `result.offset >= -1`, so the sentinel leak (errhandling-1)
could never be caught by the suite.
Diff at `tests/test_regex_portability.py:234`: assertion tightened to `result.offset >= 0`,
consistent with the construction-time clamp. Assessment: the guard now fails if `-1` ever leaks.
Accept.

### quality-1 / test-2 — Fixed  [PROMPT VERIFY ITEM 2]
Claim: `_PORTABLE_PATTERNS` listed `r"A"` labeled "4-hex unicode escape" — but `r"A"` is the
single literal byte `A`, passing for the wrong reason and leaving the `\uHHHH` (`unicode_escape`)
grammar path entirely untested.
Diff at `tests/test_regex_portability.py:126`: `r"A"` replaced with `r"A"` (the real
6-char `\u`+4-hex string); `\U00000041` (8-hex) retained at line 125.
Live verification: `r"A"` (len 6) → PORTABLE via the `unicode_escape` path; and a
3-hex truncation `\u041` → **NON-portable**, proving the path genuinely requires exactly 4 hex
digits (i.e. the test now exercises `unicode_escape`, not a literal). The literal `r"A"` is gone.
Assessment: the test now exercises a real unicode escape, not the literal byte `A`. Accept.

### test-1 — Fixed
Claim: F1/F4/F5 over-admissions were unpinned in the portability suite (no test on
`check_regex_portable` for `\07`/`a{2,1}`/`[z-a]`), so a future fix or regression goes
undetected.
Diff: added `test_f1_octal_escape_known_over_admission` (now asserts REJECT — F1 was actually
fixed via correctness-1), `test_f4_inverted_bound_known_over_admission` (asserts ACCEPT = known
CFG gap), `test_f5_reversed_class_range_known_over_admission` (asserts ACCEPT = known CFG gap),
each with rationale linking to the spike gate. Assessment: behavior pinned at the
`check_regex_portable` level with documentation; F4/F5 update-on-fix prompts present. Accept.

### test-3 — Fixed
Claim: offset-pinning tests used `result.offset > 0`, too loose to distinguish the design's
committed `longest_parse_len` source from `result.pos`.
Diff: `test_posix_class_offset_is_sensible` now asserts `result.offset >= 1` with a docstring
explaining `longest_parse_len`=1 vs `result.pos`=0 for `[[:alpha:]]`. Live verification:
`[[:alpha:]]`→offset 1 (REJECTED), so an implementation reporting `result.pos`=0 would fail.
Assessment: assertion is now falsifiable against the wrong source. Accept.

### test-5 / quality-2 — Fixed
Claim: `\A` and `\z` were duplicated in `_PORTABLE_PATTERNS` (two sections), doubling those
parametrized cases for no added coverage.
Diff: the `# Top-level anchor/control escapes` duplicates removed; `\A`/`\z` retained once under
`# Anchors`. Assessment: cosmetic, correctly resolved. Accept.

### quality-3 — Fixed
Claim: the completeness-test parametrize called `_load_grammar_regexes` eagerly in the decorator
with no `try/except`, so a missing Rust extension produced an opaque collection-time traceback
instead of the `maturin develop` hint the sister module gives.
Diff at `tests/test_regex_portability.py`: cases built once into `_RUST_TARGET_CASES` inside a
`try/except` that raises `pytest.UsageError` with the build hint, mirroring
`test_regex_grammar_corpus.py`. Assessment: matches the established pattern. Accept.

### quality-4 — Fixed
Claim: `f"...{stopped!r}..."` applied `!r` to an integer (`stopped`), a no-op that misleads
maintainers.
Diff at `regex_portability.py`: `!r` removed (`{stopped}`). Assessment: trivial, correct. Accept.

### efficiency-1 — Fixed
Claim: `check_regex_portable(term.value)` ran per `gsm.Regex` term, re-parsing a pattern used in
N rules N times, while the very next line dedups via `_regex_idx`.
Diff at `gsm2parser_rs.py:794`: the check is gated on `term.value not in self._regex_index`, so
each distinct pattern is checked once, while keeping the check at the user-term site (not inside
`_regex_idx`, preserving the design §5.3 domain boundary). Assessment: collapses N→1 per distinct
pattern; design intent preserved. Accept.

### efficiency-2 — Fixed
Claim: each Rust-target grammar (incl. the full `fegen.fltkg`) was parsed twice at collection
time — once for params, once for ids.
Diff: single `_RUST_TARGET_CASES` list built once; `_RUST_TARGET_IDS` derived from it. Aligns
with `test_regex_grammar_corpus.py`'s single-list pattern. Assessment: one parse per grammar at
collection. Accept.

## Disputed items

- **reuse-1 / TODO(regex-portability-check-reuse)**: fails rubric Q2 — the shared-helper
  extraction between `check_regex_portable` and `classify_pattern` is mechanical, single-package,
  and needs no design cycle or owner input (the reviewer spelled out the exact path; the
  responder concedes "low risk"). Per the rubric this is **do-now**, not a TODO; a TODO must be
  specifically design-work-required or owner-input-required. Need: either land the shared-helper
  refactor and convert reuse-1 to Fixed, OR supply a concrete reason the extraction genuinely
  requires deferral (not "non-trivial"/"low risk"). This is the only wrong disposition.

## Approved

20 findings: 13 Fixed verified (correctness-1/security-1, errhandling-1/quality-5,
errhandling-2, quality-1/test-2, test-1, test-3, test-5/quality-2, quality-3, quality-4,
efficiency-1, efficiency-2), 3 Won't-Do sound (correctness-2 `(?U)`, correctness-3 inverted
bound, correctness-4 reversed range), 1 TODO acceptable (test-4). All three prompt-specified
verification items confirmed: (1) the `\0` false-negative is actually flagged by the lint now,
grounded in the removed `control_escape` production; (2) quality-1's test exercises the real
`A` unicode-escape path (literal `r"A"` removed; 3-hex truncation rejects, proving the
path); (3) quality-5's offset bug is resolved by construction-time clamp, no `-1` exported.

---

## Verdict: REWORK

One disposition wrong: reuse-1 is TODO'd but is a mechanical do-now refactor (fails rubric
Q2 — no design or owner input required). Round 1, so REWORK. All other 21 findings'
dispositions are acceptable; the three prompt-flagged items (correctness `\0`, quality-1
unicode escape, quality-5 offset) all verified resolved.
