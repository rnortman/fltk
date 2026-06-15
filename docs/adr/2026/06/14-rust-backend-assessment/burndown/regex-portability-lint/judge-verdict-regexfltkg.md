# Judge verdict — design review (regex.fltkg + reconciled design.md)

Phase: design. Artifacts: `burndown/regex-portability-lint/regex.fltkg` and `design.md`. Round 1.
Notes: 1 reviewer file (`notes-regexfltkg-review.md`); 7 findings (design-1 .. design-7), plus a closing informational offset note.
Dispositions: all 7 dispositioned **Fixed**. No TODO, no Won't-Do.

**Verification method (independent).** I did not take the responder's "verified" at face value. I
(1) regenerated the parser from the *revised* `regex.fltkg` with the real toolchain
(`genparser generate ... regex_subset regex_subset_cst`) — it compiled with no GSM validation error;
(2) drove `apply__parse_regex` over the full must-accept / must-reject corpus (38 accept + 29 reject
cases) — **0 mismatches**; (3) executed BOTH engines directly on the disputed patterns — Python `re`
(stdlib; note this box is 3.14.5) and `regex_automata::meta::Regex` 0.4 (the exact crate/version in
`crates/fltk-parser-core/Cargo.toml:17`, via a throwaway probe, since removed). Engine results below
are mine, not the responder's.

This is a doc/grammar phase, so there is no "Added TODOs walk" section. Findings are all non-TODO
dispositions; they are walked below.

## Other findings walk

### design-1 — Fixed (over-admission `[^]`/`[]`)
Reviewer claim: `[^]` accepted by mis-parse (PEG fall-through let `^` be swallowed as an ordinary
`class_char`); consequence: a both-invalid pattern passes the portability lint, fails open later under
`all_regex_patterns_compile` with a worse-located error — the exact fail-open mode this lint exists to close.
Engine ground truth: `[^]` → Python `PatternError` (unterminated set), Rust `ERR`. `[]` → both `ERR`. Both reject; grammar must reject.
Grammar inspection: `char_class := %"[" . negated:"^"? . class_body . %"]"` (line 186); `class_body`
requires non-empty body (`class_item+` or `lead_dash` then items) (188-190). Negation is now an optional
prefix, not a member, so the positive/negated fall-through pair is gone.
Generated-parser run: `[^]` → SHORT pos=0; `[]` → SHORT pos=0 (both reject). `[a^b]`/`[a^]` → FULL
(literal non-leading caret still admitted — no over-rejection of literal `^`, both engines OK).
Assessment: root cause eliminated; reject is correct on both engines; no collateral over-rejection. Accept.

### design-2 — Fixed (over-admission `[\d-z]` range-with-shorthand, plus adjacent `[\b]`)
Reviewer claim: a range endpoint could be a class shorthand, so `[\d-z]`/`[a-\d]` were accepted; same
fail-open class as design-1.
Engine ground truth: `[\d-z]`/`[a-\d]` → both engines `ERR`. Adjacent (responder-found) `[\b]` → Rust
`ERR`, Python `OK` (backspace) = **divergent**; `[\A]`/`[\z]` → both `ERR`.
Grammar inspection: range endpoints draw from `class_range_atom := class_char_escape | class_char`
(212-214) where `class_char_escape := %"\\" . body:char_escape` (244-245) — `char_escape` is
control/hex/unicode/meta only, never a shorthand/assertion. Class members draw from `class_escape` whose
body is `class_shorthand | char_escape` (237-239) — excludes assertions/anchors.
Generated-parser run: `[\d-z]`,`[a-\d]`,`[\b]`,`[\B]`,`[\A]`,`[\z]` → all SHORT pos=0 (reject);
`[\d]`,`[\w\s]` (plain shorthand member) → FULL; `[\n-\r]`,`[\x41-\x5a]` (escape range endpoints) → FULL.
Assessment: fix addresses the consequence and the responder's adjacent `[\b]` divergence is real and
correctly closed (verified Rust ERR / Python OK). Accept.

### design-3 — Fixed (partial; one deliberate over-rejection) — SCRUTINIZED
Reviewer claim: literal `-` in a class (`[a-]`, `[-a]`, `[a-z-]`) over-rejected though portable;
consequence: spurious Rust build failures, "common enough (`[+\-]`, `[a-z-]`, ranges ending in dash) that
it will bite real grammars."
Engine ground truth: `[a-]`,`[-a]`,`[a-z-]`,`[+\-]`,`[-]` → both engines OK (portable). The interior
case `[a-z-0]` → both engines OK *and both match `-` literally* (portable). The genuine set-difference
look-alike `[a-z--_]` → Python `FutureWarning: Possible set difference`, Rust treats it as difference (does
NOT match `-`) = divergent.
Grammar inspection: `char_class` gains optional `lead_dash`/`trail_dash`; `class_body` has a
`lead_dash`-first alternative (188-190). `class_char` (223) still excludes `-`, so an *interior* literal
`-` between members has no production.
Generated-parser run: `[-a]`,`[a-]`,`[a-z-]`,`[+\-]`,`[-]` → FULL (accept). `[a-z-0]` → SHORT pos=0 (reject).
The scrutiny: `[a-z-0]` is genuinely portable (both engines agree it is a literal dash), yet the grammar
rejects it. This is a real over-rejection of a portable construct — the reviewer named it. BUT:
(a) every "common enough" case the reviewer's *consequence* paragraph actually enumerated — `[+\-]`,
`[a-z-]`, ranges ending in dash, leading `[-a]` — is now accepted;
(b) the residual (interior dash *after a completed range*) is the rarer shape and shares its surface form
with the `--` set-difference look-alike that genuinely diverges/warns (`[a-z--_]`, verified);
(c) the exclusion is the *safe* direction (loud build error, never silent mis-parse) and is consistent
with the grammar's explicitly-documented fail-closed philosophy (regex.fltkg lines 15-22, 170-177);
(d) it is a called-out, source-justified decision in both the grammar comment (170-177) and design §4.2
(line 256) — not a silent gap.
Per CLAUDE.md the over-rejection is also Rust-only; such a grammar still builds on the Python backend, and
the author can rewrite an interior dash into a leading/trailing position. Over-rejection here clears the
severity bar for a deliberate fail-closed call rather than a defect.
Assessment: the substantive bite is fixed; the residual is a deliberate, documented, safe-direction
over-rejection covering only a set-diff look-alike shape. Accept (noted as the one place the artifact
rejects a confirmed-portable input — see Disputed-items note, non-blocking).

### design-4 — Fixed (over-rejection of empty groups/branches; nilable-validator interaction)
Reviewer claim: empty alternation branches and empty group bodies (`()`, `(?:)`, `a|`, `|a`, `a||b`)
over-rejected though portable; AND the fix must be checked against FLTK's no-repeated-nilable-item
validator (`gsm.py:418-453`) since making `concatenation`/`alternation` nilable could trip it.
Engine ground truth: `()`,`(?:)`,`a|`,`|a`,`a||b` → both engines OK (portable).
Grammar inspection: `alternation` admits empty branch (`branch:concatenation?`) and empty right operand
(`right:concatenation?`) (68-70); nilability confined to the optional base case, growth alternatives
consume `|` or a non-nilable `repetition`.
Independent regen: the parser **regenerated with NO GSM validation error** — directly discharging the
reviewer's explicit no-repeated-nil concern (this was the load-bearing risk the reviewer flagged for regen).
Generated-parser run: all five accept FULL; no over-admission regression (every must-reject still stops short).
Side effect I checked: because `alternation` now always matches at least the empty prefix, whole-pattern
rejects return SHORT pos=0 rather than the HARDFAIL (`result is None`) the reviewer originally observed.
The design's §5.2 predicate (`result is not None and result.pos == len`) classifies SHORT pos=0 as
non-portable correctly, and reports `longest_parse_len` (not `result.pos`) — verified still meaningful
(`[[:alpha:]]`→1, `(?=x)`→2, `[\d-z]`→4, prefix `abc[[:alpha:]]`→4). Offset reporting survives the change.
Assessment: fix correct; the reviewer's regen-check concern independently confirmed; offset contract intact. Accept.

### design-5 — Fixed (completeness: `\A` `\z` `\a` `\U........`)
Reviewer claim: genuinely-portable escapes over-rejected; safe direction but spurious build failures.
Engine ground truth: `\A`,`\z`,`\a`,`\U00000041` → both engines OK (portable). For-the-record exclusions
re-checked: `\Z` → Python OK / Rust ERR (divergent, correctly excluded).
Grammar inspection: `anchor_escape := value:/[Az]/` (280) at top level only (not in any class path);
`control_escape := value:/[nrtfv0a]/` (292) adds `\a`; `unicode_escape` adds the 8-hex `\U` alternative (301-303).
Generated-parser run: `\A`,`\z`,`\a`,`\U00000041` → FULL; `\Z` → SHORT pos=0 (reject). `[\A]`/`[\z]`
remain rejected (anchors top-level only) — matches both engines (`[\A]`/`[\z]` → both ERR).
Assessment: admissions verified portable; per-context scoping (top-level only) verified against engines. Accept.

### design-6 — Fixed (drop `(?x)` verbose flag)
Reviewer claim: `x` admitted but body verbose-semantics (whitespace/`#` stripping) unmodeled; lower-stakes
(no concrete divergence found) but an unverified-equivalence admission. Reviewer's recommended option (a):
drop `x` until parity-verified.
Engine ground truth: `(?x)a b` → both engines OK (no compile divergence) — this is NOT a both-reject case;
the exclusion is a deliberate fail-closed precaution, consistent with the responder's own "no concrete
divergence found" severity note and the grammar's documented philosophy.
Grammar inspection: `flag_chars := value:/[imsU]+/` (159) — `x` removed.
Generated-parser run: `(?x)a b` → SHORT pos=0 (reject); `(?i)abc` and `(?:ab)+` → FULL (other flags intact).
Assessment: matches the reviewer's own recommended option (a); a one-character fail-closed edit aligned with
the grammar's stated default; re-admit path documented (design §5.6). Reasonable to choose Fixed over TODO —
no design cycle is owed; widening later is a localized edit. Accept.

### design-7 — Fixed (comment correctness + real `]`/`}` over-rejection it masked)
Reviewer claim: comments overstate coverage (`{`/`}` "handled"; "all metacharacters have productions").
Reviewer scored comment-only; responder found the comment masked a genuine `]`/`}` over-rejection.
Engine ground truth: `]`,`}`,`a]b`,`a}b` → both engines OK (portable literals). `a{`,`{` → Rust ERR /
Python OK (divergent — correctly kept excluded).
Grammar inspection: `literal_char := value:/[^.*+?()\[|^$\\{\n]/` (328) — excludes only openers `[`/`{`
plus metacharacters with own productions; admits closers `]`/`}`. Comment (305-328) now states this
accurately and explains the `{` divergence.
Generated-parser run: `]`,`}`,`a]b`,`a}b` → FULL; `a{`,`{` → SHORT (reject); design's own
`[\[:alpha:]]` fixture (escaped `[` + trailing literal `]`) → FULL (the draft short-rejected it; now fixed).
Assessment: responder upgraded a comment-only finding into a real over-rejection fix and verified the
divergent `{` stays excluded. Accept.

### Informational offset note (closing) — confirmed
Reviewer's closing note (whole-pattern rejects observed as HARDFAIL with usable offset) was re-confirmed
against the revised grammar, with the caveat I record under design-4: rejects are now SHORT pos=0 (empty
branch always seeds), and the design's `longest_parse_len` offset choice remains the correct, populated
source. No grammar action needed; the responder's informational reply is accurate.

## Disputed items

Nothing blocking. One non-blocking note for the record:

- **design-3 / interior literal dash (`[a-z-0]`)** — the artifact rejects a construct that is
  *confirmed portable on both engines* (both match `-` literally, no warning on this box). This is the
  only confirmed-portable input the grammar rejects. It is a deliberate, documented, safe-direction
  over-rejection guarding the `--` set-difference look-alike (`[a-z--_]`, verified divergent), and every
  common case the reviewer's consequence paragraph named is accepted. Recorded so the decision is visible;
  not grounds for REWORK. If a real downstream grammar later needs an interior literal dash, the fix is a
  localized `class_char`-with-negative-lookahead-style edit (admit interior `-` only when not followed by `-`).

## Approved

7 findings, all Fixed and verified: 7/7 dispositions accepted. Over-admission fixes (design-1, design-2
incl. adjacent `[\b]`) verified both-engine-reject; new admissions (design-5, design-7 closers) verified
both-engine-portable; over-rejection fixes (design-3 common cases, design-4 empty branches) verified
accept with clean regen; `(?x)` exclusion (design-6) matches reviewer's recommended option. Full
38-accept / 29-reject corpus run against the regenerated parser: 0 mismatches.

---

## Verdict: APPROVED

All 7 dispositions acceptable. Each "Fixed" claim independently re-verified against (a) the regenerated
parser over the full corpus (0 mismatches), (b) direct execution of both regex engines on every disputed
pattern, and (c) the grammar/design text. The one confirmed-portable input the grammar rejects (`[a-z-0]`,
design-3) is a deliberate, documented, safe-direction over-rejection covering a set-difference look-alike,
with all reviewer-named common cases accepted — non-blocking, recorded in Disputed items.
