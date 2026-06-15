# Dispositions — design review, `regex-portability-lint` (round 1)

Responder: designer. Design under review:
`burndown/regex-portability-lint/design.md`. Reviewer notes:
`burndown/regex-portability-lint/notes-design-design-reviewer.md`.

All six findings were fact-checked against source before disposition. Verified
independently: `_regex_idx` is called from both the trivia site
(`gsm2parser_rs.py:578`, `ws_idx = self._regex_idx(r"\s+")`) and the user-term site
(`gsm2parser_rs.py:758`, `idx = self._regex_idx(term.value)`); `_test_regex_empty`
compiles with `re.compile` and tests `.match("")` (`gsm.py:165-172`); the lookahead
block-comment regex `/[^*]*(?:\*(?!\/)[^*]*)*/` is in `fltk.fltkg:76` /
`bootstrap.fltkg:21` but NOT in the committed Rust target (`fegen.fltkg:21` uses the
lookahead-free `(?:[^*]|\*+[^\/\*])*`, confirmed in
`crates/fegen-rust/src/parser.rs:25` `REGEX_PATTERNS`); `fltk.fltkg` is "intentionally
broken" (`Makefile:249`); `make gencode` and per-grammar `gen-rust-parser` invocations
exist (`Makefile:226,230-231,247,280`); Python `re` rejects both `\pL` and `\p{L}` with
`bad escape \p` (executed); fixture quantified rule `items := item:atom+`
(`rust_parser_fixture.fltkg:22`) requires non-nullable operands. All findings are
accurate; none were rubber-stamped or hallucinated.

A substantial design edit followed (insertion point moved from `_regex_idx` to the
user-term site, escape-hatch recommendation reversed to "no hatch"), so the
cleanup-editor pass was re-run to reconcile §2.1, §4.2, §4.3, §5, §6, §7, §9 and the
intro section-range — contradictions introduced by the fixes were resolved in place.

---

design-1:
- Disposition: Fixed
- Action: Moved the lint insertion point from `_regex_idx` to the `gsm.Regex` branch of
  `_gen_consume_term` (`gsm2parser_rs.py:757-761`), the author-written-regex site.
  Rewrote §4.2 (now titled "Wire into the Rust generator at the user-regex term site") to
  explain that `_regex_idx` also registers the generator-internal trivia `\s+`
  (`:578`) and that linting inside it would scan that internal pattern; updated §2.1
  insertion-point paragraph, §1 trivia note, §5 "Pattern appears in multiple rules"
  bullet, §7 files-touched line, and added a §6 test pinning that a whitespace-separator
  grammar generates without a portability error.
- Severity assessment: The original design's chokepoint-and-framing mismatch was benign
  today (`\s+` passes the denylist) but would, on any future denylist row matching `\s`,
  reject every grammar with whitespace separators and emit an error naming a pattern the
  author never wrote — a latent self-inflicted breakage. Moving to the user-term site
  removes that whole class.

design-2:
- Disposition: Fixed
- Action: Added a note in §4.1 (after the detection table) stating that the POSIX
  detector intentionally extends the exploration's `\[\[:[a-z]+:\]\]` with `\^?` to catch
  the negated `[[:^alpha:]]` form (which §6 tests require flagged). Cross-references
  `exploration.md:200`.
- Severity assessment: Low. The design's regex was already the better one; the risk was
  only that an implementer cross-referencing the exploration would see two unexplained
  variants and pick the weaker one, dropping coverage of negated POSIX classes the test
  plan demands. The note removes that ambiguity.

design-3:
- Disposition: Fixed
- Action: Replaced the confused "(and bare `\p{L}` short form)" parenthetical. The
  detection regex is now `\\[pP](\{|[A-Za-z])`, which catches both the braced
  `\p{...}`/`\P{...}` and the brace-less single-letter shorthand `\pL`/`\PN`. Updated the
  §4.1 detection table row, added an explanatory note (the brace-less form is what
  `\\[pP]\{` alone would miss), and added `\pL`, `\PN` to the §6 unit-test denied-construct
  list. The "Why non-portable" column now records the verified fact that Python `re`
  rejects `\p`/`\P` outright (`bad escape \p`).
- Severity assessment: Medium. `\pL` is a real `regex-automata`/regex-syntax shorthand;
  the original `\\[pP]\{` detector would let it through as a false negative — exactly the
  Unicode-property silent-divergence class this item exists to close. The original
  parenthetical also self-contradicted the detection column. Both are now resolved.

design-4:
- Disposition: Fixed
- Action: Reversed the recommendation in §4.3 (retitled "No escape hatch in the first ship
  (hard wall)"). The `--allow-nonportable-regex` generator flag is no longer recommended;
  the design now ships with no opt-out, citing two source-grounded reasons: the flag lives
  in the Makefile build invocation (`Makefile:226,230-231,280`), divorced from the
  `.fltkg`, and it is whole-grammar (suppresses the lint for every pattern, re-opening
  silent divergence under a green build and a passing `gencode-drift-gate` regen-diff).
  Notes the in-pattern sentinel is brittle. Updated §4.4 docstring item (removed
  "escape hatch" pointer), §5 false-positive and error-message bullets, §7 (now "No edit
  to genparser.py"), removed the escape-hatch generator-integration test from §6, and
  rewrote §9 O3 to recommend "no hatch." Kept O3 as an open question because whether to
  provide any hatch is a genuine user-judgment call.
- Severity assessment: Medium. The original recommended flag was scope creep beyond the
  spec (which asks only to "reject with a clear error") and actively undercut the
  fail-closed contract the item establishes — a whole-grammar bypass would silence
  accidental future non-portable constructs alongside the one deliberate one. The reviewer
  noted the design already listed "no hatch" as an O3 option, so this is a
  recommendation-quality reversal, not a defect repair, but it materially strengthens the
  design.

design-5:
- Disposition: Fixed
- Action: Added a constraint paragraph to §4.5: added parity patterns must be non-nullable
  (or placed only in rules tolerating nullable operands), because
  `gsm.Regex.can_be_nil`/`_test_regex_empty` (`gsm.py:156-172`) feeds grammar validation
  and the fixture's quantified rules (e.g. `items := item:atom+`,
  `rust_parser_fixture.fltkg:22`) require non-nullable operands. Cites the failure mode (a
  nullable addition fails fixture *generation* on the nil-operand check, a confusing red
  unrelated to portability).
- Severity assessment: Low. A carelessly nullable fixture pattern would fail at fixture
  build, immediately and locally, but would look like a lint/parity bug rather than a
  test-authoring mistake. The one-line constraint prevents that confusion.

design-6:
- Disposition: Fixed
- Action: Added a "Known in-tree near-miss" paragraph to §6 recording that the
  negative-lookahead block-comment regex in `fltk.fltkg:76` / `bootstrap.fltkg:21` will
  (correctly) trip the lint if ever Rust-generated, that neither is a committed Rust target
  (the committed parser comes from `fegen.fltkg`, whose `block_comment` is lookahead-free —
  verified in `crates/fegen-rust/src/parser.rs:25`), that `fltk.fltkg` is "intentionally
  broken" (`Makefile:249`), and that the regen-confirm verification step must not run the
  lint against those two grammars and read the flag as a finding.
- Severity assessment: None to correctness — the design's "no committed grammar trips the
  lint" claim is accurate. The note prevents an implementer from running the
  regen-verification step against the intentionally-broken grammars and misreading a
  correct lint flag as a regression.
