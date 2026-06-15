# Dispositions — design review round 2 (`regex-portability-lint`, grammar-based design)

Responder pass over `notes-design2-design-reviewer.md`. Design under review:
`design.md`. The grammar-based approach is authoritative (user directive,
`notes-design-user.md`); these dispositions do not revisit it.

All five findings were fact-checked against source at the current tree and found
grounded. All five are **Fixed** in `design.md`. Substantial edits → cleanup-editor
re-run (terminology normalized, leaked review-ID tags stripped, contradictions
resolved). Summary below.

---

design-1:
- Disposition: Fixed
- Action: Added a new hard authoring constraint bullet to §4.3 ("Escape `/` inside
  the validator grammar's own regex terminals"): every `/` in `regex_subset.fltkg`'s
  own regex terminals must be written `\/` (and `\` as `\\`), because the `.fltkg`
  `raw_string` body grammar is `value:/([^\/\n\\]|\\.)+/` (`fegen.fltkg:17`) and a bare
  `/` closes the regex terminal early. Strengthened the §7 whole-tree completeness test
  to state it also serves as the leaf-matcher correctness guard (it parses the real
  in-tree `([^\/\n\\]|\\.)+`), and added an explicit positive-control round-trip test
  pinning that the committed `regex_subset_parser.py` came from a clean
  `regex_subset.fltkg` (discharging the §6 "drifting from its grammar" bullet as a
  committed gate). Verified the `.fltkg` body grammar at `fegen.fltkg:17`.
- Severity assessment: The regex-subset grammar is the security boundary; a leaf rule
  mis-tokenized on a bare `/` silently over- or under-admits and surfaces as a confusing
  generation error far from its cause. Pinning the constraint and adding committed tests
  converts a silent authoring slip into a loud, located failure.

design-2:
- Disposition: Fixed
- Action: Rewrote §5.2 to commit to a single error-offset source and stop conflating
  it with `result.pos`. Accept/reject predicate = `result is not None and result.pos ==
  len(pattern)`; reported error offset = `parser.error_tracker.longest_parse_len`
  (furthest progress), the same field FLTK's `format_error_message` uses
  (`errors.py:25-49,126-152`). Documented that `error_tracker` is populated for a pure
  recognizer regardless of labels/dispositions, since `fail_regex`/`fail_literal` fire
  from `consume_regex`/`consume_literal` on every terminal-consume failure keyed on the
  current rule frame (`fltk_parser.py:85,95`) — verified, which also corrects the
  reviewer's slightly-off parenthetical that error tracking "keys off rule-application
  frames" (it keys off terminal-consume failure with the current frame, always present).
  Propagated the `longest_parse_len` wording into §2, §4.2, §5.3, §6 (two bullets), the
  `RegexPortabilityIssue.offset` comment, and the §7 offset-assertion test (now asserts
  the furthest-progress value, pinning the design's choice rather than recording whatever
  the implementation emits). Verified `ApplyResult` shape (`memo.py:68-71`) and
  `ErrorTracker.longest_parse_len` (`errors.py:25-37`).
- Severity assessment: Without committing to an offset source, an implementer could ship
  `result.pos` (an unhelpful number just past a matched prefix) and write the tests to
  whatever it emitted, degrading the requirement's "clear, located error" to a present
  but unhelpful number. Pinning `longest_parse_len` makes the located-error requirement
  meaningful and the tests load-bearing.

design-3:
- Disposition: Fixed
- Action: Restructured the §6 residual into an explicit "residual ledger" listing
  `\d`/`\w`/`\s` (with negations), `(?i)`, and now `\b`/`\B` (defined in terms of `\w`,
  so they inherit `\w`'s non-ASCII divergence; codebase already names `\ba*` as a
  static-checker blind spot at `gsm.py:439-444`, verified). Propagated `\b`/`\B` into the
  §3 "one honest limit" paragraph, the §4.1 escape bullet (admitted-as-ASCII-portable
  with a residual pointer parallel to the `(?i)` treatment), O2 (full ledger; the
  `TODO(regex-unicode-class-divergence)` must name `\b`/`\B`), and a `\bword\b` positive
  unit-test case in §7.
- Severity assessment: `\b`/`\B` were admitted-as-portable in §4.1 but absent from the
  residual ledger, so the `document-scope-boundary` hand-off would silently omit a
  divergent-over-non-ASCII construct — the exact silent-divergence class this item exists
  to surface. Adding them to the ledger closes the internal-consistency gap.

design-4:
- Disposition: Fixed
- Action: Corrected §7's factual mischaracterization — only three committed grammars are
  fed to `gen-rust-parser` and reach the production check (`fegen.fltkg`,
  `rust_parser_fixture.fltkg`, `collision_fixture.fltkg`; `Makefile:230-231,280,285-286`);
  `poc_grammar.fltkg` and `phase4_roundtrip.fltkg` are `gen-rust-cst`-only
  (`Makefile:269-272`) and the parser check never runs against them in production. The
  test now asserts the parser-target set strictly and labels CST-only grammars as a
  clearly-marked bonus. Added an explicit drift-surface resolution: derive the
  parser-target list from a single source the Makefile and test share (committed manifest
  or agreed glob), or, if single-sourcing is deferred to keep scope, keep the manual list
  with a `TODO(regex-portability-target-list-drift)` (TODO.md + comment) tying it to the
  `gencode-drift-gate` family. Verified the Makefile gencode recipe distinguishes
  `gen-rust-parser` from `gen-rust-cst` targets exactly as the finding states.
- Severity assessment: Lower than 1-3 (the §5.3 production check is the real gate; this
  is a test-only completeness aid). But the hardcoded list is the project's named
  hand-maintained-per-target-list anti-pattern: a future parser-target fixture with a
  non-portable regex would slip past the completeness test until someone remembered to
  enumerate it. Single-sourcing (or a tracked TODO) removes the silent-drift hole.

design-5:
- Disposition: Fixed
- Action: Rewrote §9's second non-goal bullet to (a) quote the requirement's STATUS
  preference for standardization ("Do this *OR* better if possible…",
  `recommended-actions-eli5.md:122` — verified; the reviewer mis-attributed it to
  `recommended-actions.md`, but the line genuinely exists in the eli5 requirement source),
  and (b) add an honest qualifier that `exploration.md:320-328` leaves the deciding fact
  for the `regex`-PyPI-as-common-ground sub-option (shared Unicode-DB source/version)
  unresolved, so standardization is a deliberate acknowledged deferral, not a closed
  finding. Stated the lint is correct irrespective of how that question resolves (even the
  larger common subset "is still not perfectly identical", `exploration.md:294`) and
  routed the open question to `differential-property-harness`/`document-scope-boundary`.
- Severity assessment: Groundedness/honesty gap on the one place the requirement asked
  for a judgment call. Does not change the recommendation (the lint is needed either way),
  but presenting "no shipping library can satisfy" as settled while the cited exploration
  flags a sub-branch as open is an overstatement; the qualifier keeps the non-goal honest.
