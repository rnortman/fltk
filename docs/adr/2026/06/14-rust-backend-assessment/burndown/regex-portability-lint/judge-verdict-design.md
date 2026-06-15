# Judge verdict — design review

Phase: design (burndown item `regex-portability-lint`).
Design: `burndown/regex-portability-lint/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 6 findings. All dispositioned Fixed.

This is a doc phase, so there is no Added-TODOs walk. Every finding is a non-TODO
disposition (all Fixed) and is walked below against the design text and cited source.

## Other findings walk

### design-1 — Fixed
Claim: the lint is placed inside `_regex_idx`, but that dedup table is called from
TWO sites — the user `gsm.Regex` term (`gsm2parser_rs.py:758`) AND the
generator-internal trivia `\s+` (`gsm2parser_rs.py:578`). Consequence: benign today
(`\s+` passes the denylist), but the design's framing ("fires only for user-grammar
regexes") is false at the chosen chokepoint, and any future denylist row matching
`\s` would reject every grammar with whitespace separators, erroring on a pattern
the author never wrote.
Source check: confirmed. `gsm2parser_rs.py:578` is `ws_idx = self._regex_idx(ws_pattern)`
with `ws_pattern = r"\s+"` inside the `is_trivia_rule` branch; `:757-758` is the
`gsm.Regex` branch calling `idx = self._regex_idx(term.value)`. `_regex_idx`
(`:136-141`) is the single shared dedup table. Real consequence, real source.
Disposition check: §4.2 retitled "Wire into the Rust generator at the user-regex
term site"; design now places the lint at the `gsm.Regex` branch of
`_gen_consume_term` (`:757-761`), explicitly NOT inside `_regex_idx`, and explains
the trivia-pattern reason (§4.2, §1 trivia note at :59-64, §2.1, §5 multiple-rules
bullet, §7 files-touched). §6 adds a test pinning that a WS-separator grammar
generates without a portability error. The fix relocates the lint to the
author-written-regex site, which is exactly the reviewer's primary suggested fix.
Assessment: fix addresses the consequence at the named site. Accept.

### design-2 — Fixed
Claim: §4.1 POSIX detector `\[\[:\^?[a-z]+:\]\]` silently diverges from the
exploration's `\[\[:[a-z]+:\]\]` (adds `\^?`); the `\^?` is correct (catches
`[[:^alpha:]]`, which §6 tests require) but the change is unexplained, risking an
implementer picking the weaker exploration regex. Consequence: low — only ambiguity.
Source check: `exploration.md:200` is `re.search(r'\[\[:[a-z]+:\]\]', pattern)` —
confirmed it lacks `\^?`. Self-tested the design's regex: matches `[[:alpha:]]` and
`[[:^alpha:]]`, does not match escaped `[\[:alpha:]]`. The `\^?` extension is real
and correct.
Disposition check: §4.1 now carries an explicit note (design.md:236-240) that the
POSIX detector intentionally extends the exploration's regex with `\^?` to catch the
negated form, with the `exploration.md:200` cross-reference. Matches the suggested fix.
Assessment: note resolves the documented ambiguity. Accept.

### design-3 — Fixed
Claim: §4.1 "(and bare `\p{L}` short form)" parenthetical is self-contradictory —
`\p{L}` already begins with `\p{` so `\\[pP]\{` matches it; the genuinely distinct
brace-less form is `\pL`, which `\\[pP]\{` does NOT match. Consequence: medium — if
brace-less `\pL`/`\PN` are a real divergence vector they slip as false negatives,
exactly the Unicode-property silent-divergence class the item exists to close.
Source check: confirmed `\pL`/`\p{L}` both rejected by Python `re` (`bad escape \p`),
both accepted by `regex-automata`. The design's new detector `\\[pP](\{|[A-Za-z])`
self-tested: matches `\p{L}`, `\P{N}`, `\pL`, `\PN`; does not match `\\p` (escaped
backslash then literal p). Real false-negative gap; real fix.
Disposition check: §4.1 detector changed to `\\[pP](\{|[A-Za-z])` (design.md:230,
:240-242); confused parenthetical replaced; `\pL`, `\PN` added to the §6 unit-test
denied-construct list (design.md:397-398) and to the clean false-positive guards
(`\\p` clean). Matches the "extend the detector AND list `\pL` in §6 tests" branch
of the suggested fix.
Assessment: detector now covers the brace-less shorthand; tests pin it. Accept.

### design-4 — Fixed
Claim: §4.3/§9-O3 recommended a `--allow-nonportable-regex` generator flag that
undercuts the fail-closed contract — the flag lives in the Makefile invocation
(`Makefile:226,230-231,280`), divorced from the `.fltkg`, and is whole-grammar, so
silencing one deliberate `[[:alpha:]]` also silences accidental future non-portable
constructs under a green build and a passing `gencode-drift-gate` regen-diff.
Reviewer explicitly framed this as a recommendation-quality concern (the design
already listed "no hatch" as an O3 option), not a hidden defect; the spec asks only
to "reject with a clear error."
Source check: `Makefile:226` is the per-grammar `gen-rust-parser` invocation; :230-231
and :280 are the committed-parser regen invocations. The whole-grammar / build-script-
audit weaknesses are real. The spec wording ("reject them with a clear error message")
is in the eli5 doc per the design's citation; the flag is indeed more than the spec asks.
Disposition check: §4.3 retitled "No escape hatch in the first ship (hard wall)";
the flag is no longer recommended; both source-grounded reasons recorded (build-script
location; whole-grammar granularity). §4.4 docstring pointer, §5 bullets, §7 ("No edit
to genparser.py"), §6 (escape-hatch integration test removed), and §9 O3 ("no hatch"
recommended, kept open because whether to provide any hatch is genuine user judgment)
all reconciled. This is the reviewer's leaned-toward outcome (ship with no hatch).
Assessment: recommendation reversed to the safer, spec-matching posture; O3 correctly
preserved as an open question for the user. This is a strengthening, not a defect
repair, but the disposition is sound and internally consistent. Accept.

### design-5 — Fixed
Claim: §4.5's new parity patterns (anchors, `(?i)`) risk interacting with
`gsm.Regex.can_be_nil`/`_test_regex_empty` (`gsm.py:165-172`), which compiles each
pattern and tests `.match("")` to feed grammar validation; a nullable addition could
fail fixture GENERATION on the nil-operand check (fixture rules like `items :=
item:atom+` require non-nullable operands), producing a confusing red unrelated to
portability. Consequence: low (caught at fixture build) but misleading.
Source check: `gsm.py:165-172` confirmed — `_test_regex_empty` does `re.compile(...)`
then `.match("")`. `rust_parser_fixture.fltkg:22` is `items := item:atom+`. Real
interaction.
Disposition check: §4.5 adds a constraint paragraph (design.md:342-350) requiring
added parity patterns to be non-nullable (or placed only in rules tolerating nullable
operands), citing the failure mode and the source. Matches the suggested fix.
Assessment: constraint added with rationale. Accept.

### design-6 — Fixed
Claim: §6's "no committed grammar trips the lint" is verified TRUE, but the design
omits that `fltk.fltkg:76` / `bootstrap.fltkg:21` contain a negative-lookahead
block-comment regex `/[^*]*(?:\*(?!\/)[^*]*)*/` the denylist flags; neither is a
committed Rust target (committed parser comes from `fegen.fltkg`, whose block_comment
is lookahead-free), and `fltk.fltkg` is "intentionally broken". An implementer
running the regen-confirm step against those grammars could misread a correct flag as
a regression. Consequence: none to correctness; value is preventing a misread.
Source check: confirmed `fltk.fltkg:76` and `bootstrap.fltkg:21` use the lookahead
form `(?:\*(?!\/)...)`; `fegen.fltkg:21` uses the lookahead-free
`(?:[^*]|\*+[^\/\*])*`; committed `crates/fegen-rust/src/parser.rs:25` REGEX_PATTERNS
contains `(?:[^*]|\\*+[^\\/\\*])*` (lookahead-free); `Makefile:230-231,277` generate
the committed parser from `fegen.fltkg`; `Makefile:249` marks `fltk.fltkg`
intentionally broken. All verified.
Disposition check: §6 adds a "Known in-tree near-miss" paragraph (design.md:434-442)
recording exactly these facts and instructing the regen-confirm step not to run the
lint against `fltk.fltkg`/`bootstrap.fltkg`. Matches the suggested fix.
Assessment: note added; correctness claim was already accurate. Accept.

## Disputed items

None. All six Fixed dispositions verify against source and the design text.

## Approved

6 findings: 6 Fixed verified (design-1 insertion-point relocation; design-2 POSIX
`\^?` note; design-3 brace-less `\pL`/`\PN` detector + tests; design-4 escape-hatch
reversal to no-hatch; design-5 non-nullable parity constraint; design-6 in-tree
near-miss note). No Won't-Do, no TODO dispositions.

Note for the record (not a disputed item, no action required): the design specifies
detection *regexes* but the escaping-aware scanner behavior (e.g. not matching across
an escaped `\[`, and the `\\p` false-positive guard) is an implementation obligation
the design correctly assigns to the scanner and pins with §6 tests. Confirmed the
specified detectors behave as claimed on the §6 example inputs; full escaping
correctness is a code-phase concern, appropriately deferred to implementation + tests,
not a design gap.

---

## Verdict: APPROVED

All six dispositions acceptable. Every Fixed claim verified against the cited source
and the design text. The two recommendation-quality findings (design-4 escape hatch,
design-6 near-miss note) were addressed substantively rather than waved off, and O1/O2/
O3/O4 are correctly preserved as user-judgment open questions rather than silently
decided. No fundamental disagreement; no scope-N pile (single coherent design, the
STATUS "OR better" gate is honestly weighed in §2-§3). Ready for the design gate (O1).
