# Judge verdict — regex-portability-lint (design phase, round 2 review)

Phase: design (grammar-based redesign, directive-driven). Doc: `design.md`.
Round 1 (judge). Base `f1e1fef` (matches reviewer note).
Notes: `notes-design2-design-reviewer.md` — 5 findings, all dispositioned **Fixed**.
User directive (`notes-design-user.md`): grammar-based validator is authoritative — not
revisited by reviewer or judge.

No added-TODOs walk (doc phase). Findings walked below; each Fixed disposition verified
against the design text and against source ground truth.

## Other findings walk

### design-1 — Fixed
Claim: design asserts the validator's own leaf matchers are "safe" but never states the
load-bearing property — that those leaf regexes must be authorable within the `.fltkg`
`raw_string` body (`([^\/\n\\]|\\.)+`), where a bare `/` closes the terminal early.
Consequence: a mis-tokenized leaf rule silently over/under-admits at the security boundary,
surfacing as a confusing generation error far from cause.
Source check: `fegen.fltkg:17` confirmed `raw_string := value:/([^\/\n\\]|\\.)+/` — bare `/`
forbidden in the body, `\\` special. Finding is grounded.
Disposition: design now adds a hard authoring-constraint bullet to §4.3 (lines 235-248):
every `/` in the validator's own terminals written `\/`, every `\` written `\\`, with the
`/[\/]/`-mis-tokenization failure mode spelled out. §7 (lines 504-510) strengthens the
whole-tree completeness test to double as the leaf-matcher correctness guard (it parses the
real in-tree `([^\/\n\\]|\\.)+`), and adds a positive-control round-trip test (lines 548-553)
pinning that committed `regex_subset_parser.py` came from a clean `regex_subset.fltkg`.
Assessment: addresses both halves of the finding (authoring constraint + committed test that
makes the slip loud). Fix is real and at the named sections. Accept.

### design-2 — Fixed
Claim: §5.2 conflates two distinct values — the accept/reject predicate and the reported
error offset — and `result.pos` on a hard fail is `None`; the design never commits to which
offset is reported, letting an implementer ship an unhelpful `result.pos` and write tests to
match, degrading the "clear, located error" requirement.
Consequence: located-error requirement degrades to a present-but-unhelpful number; tests
rubber-stamp whatever is emitted.
Source check: `ApplyResult` is `(pos, result)`, start rule returns `ApplyResult | None`
(`memo.py:68-71`) — confirmed. `ErrorTracker.longest_parse_len` is the furthest-progress
field, set by `fail_regex`/`fail_literal` on every terminal-consume failure
(`errors.py:25-49`), and `format_error_message` reads exactly that field (`errors.py:126-152`)
— confirmed. The disposition's correction of the reviewer's "keys off rule-application
frames" parenthetical is right: it keys off terminal-consume failure with the current frame
(`fltk_parser.py:85,95`).
Disposition: §5.2 rewritten (lines 311-339) to separate predicate (`result is not None and
result.pos == len(pattern)`) from reported offset (`error_tracker.longest_parse_len`), with
explicit rationale for why `longest_parse_len` beats `result.pos` for a deliberately-not-
matching recognizer. Choice propagated to §2, §4.2, §5.3, §6, the dataclass comment, and the
§7 offset-assertion test (now pins the furthest-progress value, lines 476-481).
Assessment: design commits to a single offset source, confirms it is populated for a pure
recognizer, and the §7 test pins the choice rather than recording emitted behavior — exactly
the reviewer's suggested fix. Accept.
Residual note (not a finding, not blocking): §6 (line 437) says `longest_parse_len` "is `0`
when no terminal advanced," while §5.2 (line 326) correctly says the field is `-1` until the
first terminal failure. For a hard fail at pos 0 the first consume sets it to `0`, so the
common case holds; a `-1` could in principle leak only if the start rule returns `None`
without any terminal-consume attempt. This is a one-line implementer clamp, the reviewer did
not raise it, and it does not affect the predicate or any dispositioned fix. Out of scope for
REWORK.

### design-3 — Fixed
Claim: `\b`/`\B` admitted as portable in §4.1 but absent from the §6/O2 residual ledger,
despite being defined in terms of `\w` and thus inheriting the identical non-ASCII Unicode-DB
divergence the design quarantines for `\d`/`\w`/`\s`. Internal-consistency gap: admitted-as-
portable but missing from the residual that the `document-scope-boundary` hand-off reads.
Consequence: a non-ASCII `\b` grammar passes silently and still diverges cross-backend — the
exact outcome the item exists to prevent — yet the documentation hand-off omits it.
Source check: `gsm.py:439-444` NOTE names `\ba*` (and `(?=x)`) as zero-width patterns the
emptiness checker cannot see — confirmed; codebase already treats `\b` as a static-checker
blind spot. Finding grounded.
Disposition: §6 restructured into an explicit residual ledger (lines 412-429) listing
`\d`/`\w`/`\s` (+ negations), `(?i)`, and now `\b`/`\B` with the `\w`-derivation rationale and
the `gsm.py:439-444` citation. Propagated to §3 (line 163), §4.1 (line 192), O2 (lines
624-629, with the `TODO(regex-unicode-class-divergence)` required to name `\b`/`\B`), and a
`\bword\b` positive unit case in §7 (line 472).
Assessment: closes the internal-consistency gap end to end — admission site, residual ledger,
documentation hand-off, and TODO all now name `\b`/`\B`. Matches the reviewer's option (a).
Accept.

### design-4 — Fixed
Claim: §7's "Rust-target grammars" list was factually wrong (`poc_grammar.fltkg`,
`phase4_roundtrip.fltkg` are CST-only, not parser targets), and the hand-maintained list is
itself the project's named drift anti-pattern with no sync mechanism.
Consequence: completeness guard mischaracterizes its own coverage; a future parser-target
grammar with a non-portable regex slips past until someone remembers to enumerate it. Lower
severity (§5.3 production check is the real gate).
Source check: Makefile confirms exactly three `gen-rust-parser` invocations — `fegen.fltkg`
(line 230-231), `rust_parser_fixture.fltkg` (line 280), `collision_fixture.fltkg` (lines
285-286) — and `poc_grammar.fltkg` / `phase4_roundtrip.fltkg` are `gen-rust-cst`-only (lines
269-272). The factual correction is exactly right.
Disposition: §7 corrected (lines 515-525) to assert the parser-target set strictly and label
CST-only grammars as a clearly-marked bonus; adds an explicit drift-surface resolution (lines
534-546): single-source the parser-target list (shared manifest/glob) OR keep manual with a
`TODO(regex-portability-target-list-drift)` (TODO.md + comment, per CLAUDE.md) tied to the
`gencode-drift-gate` family.
Assessment: fixes both the factual error and the structural drift weakness; the
single-source-or-tracked-TODO resolution is the reviewer's suggested fix and conforms to the
project TODO convention. Accept.

### design-5 — Fixed
Claim: the requirement STATUS prefers standardization ("Do this *OR* better if possible"), and
the design disposes of it as conclusively closed while its own cited exploration
(`exploration.md:320-328`) flags the `regex`-PyPI-as-common-ground Unicode-DB fact as
unresolved. Groundedness/honesty gap on the one place the requirement asked for a judgment
call.
Consequence: design overstates "no shipping library can satisfy" as settled when a sub-branch
is open; does not change the recommendation but leaves the non-goal dishonest.
Source check: `recommended-actions-eli5.md:122` is verbatim the STATUS line "Do this *OR*
better if possible: standardize python and rust on some regex library/standard…" — confirmed.
The disposition's correction of the reviewer's mis-attribution (eli5, not
`recommended-actions.md`) is right.
Disposition: §9 second non-goal rewritten (lines 594-612) to quote the STATUS preference, add
the honest qualifier that `exploration.md:320-328` leaves the deciding Unicode-DB fact open
(deliberate acknowledged deferral, not a closed finding), state the lint is correct
irrespective of that resolution (`exploration.md:294`), and route the open question to
`differential-property-harness` / `document-scope-boundary`.
Assessment: matches the reviewer's suggested one-sentence acknowledgement and then some;
non-goal is now honest without changing the recommendation. Accept.

## Disputed items

None. All five Fixed dispositions verified present in the design and addressing the stated
consequence. (design-2 carries a minor §5.2/§6 `-1`-vs-`0` wording inconsistency noted
above — implementer-scope, not raised by the reviewer, not disputed.)

## Approved

5 findings: 5 Fixed verified (design-1 authoring constraint + committed leaf-matcher test;
design-2 single committed offset source with pinned test; design-3 `\b`/`\B` added across
ledger/O2/TODO/test; design-4 parser-target list corrected + drift resolution; design-5
non-goal honesty qualifier). Two conditional TODO commitments
(`regex-unicode-class-divergence`, `regex-portability-target-list-drift`) are correctly tied
to TODO.md + comment per CLAUDE.md.

---

## Verdict: APPROVED

All five reviewer findings were grounded against source and all five Fixed dispositions
verify in the design text at the named sections. No disposition is hand-wavy; each fix
addresses the finding's stated consequence, not just its surface. No scope-N escalation
trigger (this is a single coherent design, no material omission deferred). Round-1 APPROVED.
