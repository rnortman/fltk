# Adversarial review: `regex.fltkg` (portable-regex-subset grammar, first draft)

Target: `docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/regex.fltkg`
Base commit: a4b35b8 (== HEAD).
Reviewed ONLY the grammar file. Authority for `.fltkg`: `docs/fltk-grammar-reference.md`.

**Verification method.** I generated the parser from the draft grammar with the real
toolchain (`uv run python -m fltk.fegen.genparser generate <grammar> regex_subset regex_subset_cst`)
— it compiled with no GSM validation error — and drove the generated `apply__parse_regex`
over a corpus. Portability claims were checked by executing both engines directly: Python
`re` (stdlib) and `regex_automata::meta::Regex` 0.4 (the exact crate/version from
`crates/fltk-parser-core/Cargo.toml:17`, via a throwaway example in that crate, since
removed). All probe artifacts were cleaned up; the repo is clean.

**What is correct (so the findings below are read in context).** The grammar is
syntactically valid `.fltkg`, generates cleanly, and on the design's own corpus behaves
exactly as intended: all 17 portable cases fully consume to end-of-input; all 13
divergent/unsupported cases (`[[:alpha:]]`, `\p{L}`, `[a-z&&...]`, `(?=x)`, `\1`,
`(?P=name)`, …) are rejected. The self-escaping in the grammar's own regex terminals
(`meta_escape`, `class_char`, `literal_char`) is correct: each stored-verbatim leaf class is
a valid Python `re` class matching the intended characters (verified). The
whitespace-significance constraint (design §4.3) holds: literal space/tab in a subject
pattern is consumed (`"a b"` → full consume), and the auto-injected `_trivia` rule is
defined but never invoked from the regex parse path (confirmed in the generated parser:
`_trivia` appears only in its own cache and helper methods, never called from
`regex`/`alternation`/`concatenation`). The left-recursive `alternation`/`concatenation`
seeds resolve; offset reporting via `longest_parse_len` lands at the right spot on
prefix-portable/non-portable-tail inputs (e.g. `abc[[:alpha:]]` → 4). These were the
design's load-bearing risks and they check out.

The findings below are genuine grammar errors, ordered roughly by stakes.

---

## design-1 — Over-admission: `[^]` is accepted but BOTH engines reject it (false negative)

**Quote / location:** `negated_class := %"[^" . items:class_item+ . %"]"` and
`positive_class := %"[" . items:class_item+ . %"]"` (lines 134–135); `char_class :=
negated_class | positive_class` (130–132).

**What's wrong:** The grammar accepts `[^]` (verified: generated parser fully consumes,
pos=3). It does so by *mis-parsing*: `negated_class` fails (after `[^`, the next char `]`
cannot start a `class_item`), so PEG falls through to `positive_class`, which reads `[` then
`^` as an ordinary `class_char` (line 158 `class_char` does not exclude `^`) then `]`. The
result is "a positive class containing `^`."

**Why (source-backed):** Executed both engines on `[^]`: Python `re` raises
`PatternError` (unterminated character set — it reads `^` as negation and `]` as the first
member), and `regex_automata::meta::Regex::new("[^]")` returns `Err`. So `[^]` is
**non-portable** (in fact rejected by both), yet the subset grammar — whose whole job is to
*reject* non-portable input — accepts it.

**Consequence:** A non-portable / both-invalid pattern passes the portability lint. This is
exactly the over-admission failure mode the design names in §6 ("a too-loose char-class body
… a non-portable pattern passes") and the class of hole this burndown item exists to close.
It is silent: the lint would green-light `[^]`, then the Rust `all_regex_patterns_compile`
test (or the Python `re.compile`) would fail later with a less-located error — defeating the
"reject at generation time with a clear message" requirement
(`recommended-actions-eli5.md` `regex-portability-lint`).

**Suggested fix:** Make the empty-negated-class shape unrepresentable, e.g. require that a
class with a leading `^` go only through `negated_class` and never let `^` be swallowed as an
ordinary `class_char` when it is the first body char. Pin `[^]` as a must-reject test
(the design's §7 rejection-test list does not currently include it).

---

## design-2 — Over-admission: `[\d-z]` (range with shorthand endpoint) accepted; BOTH engines reject

**Quote / location:** `class_range := lo:class_atom . %"-" . hi:class_atom ;` (line 142),
where `class_atom := escape | class_char` (151–153) and `escape` admits
`class_shorthand` (`\d \w \s …`, line 183).

**What's wrong:** Because a range endpoint is a `class_atom`, and a `class_atom` may be an
`escape`, and an `escape` may be a class shorthand, the grammar accepts `[\d-z]` and
`[a-\d]` as ranges (verified: `[\d-z]` fully consumes, pos=6).

**Why (source-backed):** Executed both engines: Python `re` raises `PatternError: bad
character range \d-z`; `regex_automata::meta::Regex::new` returns `Err` for both `[\d-z]`
and `[a-\d]`. A character-class range may not use a class shorthand (`\d`, `\w`, …) as an
endpoint in *either* engine — these are invalid, hence non-portable.

**Consequence:** Same class as design-1 — a both-invalid construct passes the allowlist.
The lint reports "portable" for a pattern that fails to compile on Rust, so the failure
re-surfaces later as an opaque `regex-automata` compile error rather than the clear
generation-time rejection the requirement asks for.

**Suggested fix:** A range endpoint must be a single literal/escaped *character*, not a
shorthand/assertion. Split `class_atom` so `class_range` endpoints draw from a
character-only production (single char or `\`-escaped char / `\x` / `\u`), excluding
`class_shorthand`/`assertion`. Add `[\d-z]` to the must-reject tests.

---

## design-3 — Over-rejection: literal `-` in a class (`[a-]`, `[-a]`, `[a-z-]`) rejected, though portable

**Quote / location:** `class_char := value:/[^\\\]\[\-\n]/ ;` (line 158, excludes `-`);
`class_item := class_range | class_member` (138–140); `class_range` requires a trailing
`hi:class_atom` after `%"-"` (142).

**What's wrong:** A literal `-` inside a class — trailing (`[a-]`), leading (`[-a]`), or
after a completed range (`[a-z-0]`) — has no production. `class_char` excludes `-`, and
`class_range` consumes `-` only when a `hi` endpoint follows. Verified: `[a-]`, `[-a]`,
`[a-z-0]` all HARD-FAIL in the generated parser.

**Why (source-backed):** Executed both engines: Python `re` and `regex_automata` both
accept `[a-]`, `[-a]`, `[a-z-0]` (a `-` in those positions is an ordinary literal). These
are textbook, common, genuinely portable class patterns.

**Consequence:** Valid downstream grammars using a literal `-` in a class are rejected at
Rust generation time — a spurious build failure. This is the "under-admission = false
positive" mode the design flags in §6 as "a loud, fixable build error," i.e. the *safe*
direction, but it is common enough (`[+\-]`, `[a-z-]`, character ranges that end with a
dash) that it will bite real grammars and force needless rewrites. Note the grammar's own
in-tree corpus does not exercise it, so the design's "every in-tree regex parses clean"
completeness test (§7) would NOT catch this.

**Suggested fix:** Add a literal-`-` `class_member` alternative (or allow `-` as a
`class_char` in non-range position). Add `[a-]`/`[-a]` to the must-accept tests.

---

## design-4 — Over-rejection: empty groups and empty alternation branches rejected, though portable

**Quote / location:** `capturing := %"(" . body:alternation . %")"` (113);
`non_capturing := %"(?:" . body:alternation . %")"` (108);
`alternation := left:alternation . %"|" . right:concatenation | branch:concatenation` (49–51);
`concatenation := head:concatenation . tail:repetition | single:repetition` (54–56).

**What's wrong:** Every branch bottoms out in at least one `repetition`→`atom`, so an empty
alternative or empty group body is unrepresentable. Verified: `()`, `(?:)`, `a|`, `|a` are
all rejected by the generated parser (`()`→HARD-FAIL, `a|`→SHORT, `|a`→HARD-FAIL).

**Why (source-backed):** Executed both engines: Python `re` and `regex_automata` accept
`()`, `(?:)`, `a|`, `|a`, `a||b` (empty group matches the empty string; an empty
alternation branch is the empty-match alternative). All are portable.

**Consequence:** Spurious rejection of valid, portable grammars that use an empty group or
an empty alternative (e.g. `(foo|)` for "optional foo"). Over-rejection (safe direction),
but a real completeness gap not covered by the in-tree corpus test. Note: the design's start
rule comment (line 42–43) says the empty *whole* pattern is handled by the caller, but says
nothing about empty *sub*-expressions/branches, which are a different, admissible case.

**Suggested fix:** Allow an empty `alternation` branch and empty group body. This interacts
with FLTK's no-repeated-nilable-item rule (`gsm.py:418-453`) — making `concatenation`/
`alternation` nilable must be checked against that validator; the current grammar generated
clean precisely because nothing is nilable, so this fix needs a regen check.

---

## design-5 — Completeness: genuinely-portable escapes excluded (`\A`, `\z`, `\U{8-hex}`, `\a`)

**Quote / location:** `escape_body := class_shorthand | assertion | control_escape |
hex_escape | unicode_escape | meta_escape` (174–180); `assertion := value:/[bB]/` (186);
`control_escape := value:/[nrtfv0]/` (189); `unicode_escape := %"u" . 4-hex` (195);
`hex_escape := %"x" . 2-hex` (192).

**What's wrong / why (source-backed):** Executed both engines:
- `\A` (start anchor) and `\z` (end anchor): accepted by both Python `re` and
  `regex_automata` → portable, but the grammar admits only `^`/`$` and `\b`/`\B`, so `\A`
  and `\z` are rejected.
- `\U00000041` (8-hex codepoint escape): accepted by both → portable, but `unicode_escape`
  admits only the 4-hex `\u` form.
- `\a` (bell): accepted by both → portable, but `control_escape` is only `[nrtfv0]`.
- (Correctly excluded, for the record: `\Z` — Python accepts, Rust rejects; `\x{..}` /
  `\u{..}` braced — Rust accepts, Python rejects; `\07` octal — Python accepts, Rust
  rejects. The grammar rightly rejects all of these.)

**Consequence:** Over-rejection of common portable constructs (`\A`/`\z` especially are
standard anchors). Safe direction, but spurious build failures for grammars that use them.
The design's §4.1 "admitted shorthands" list is the spec the grammar implements, and that
list itself omits `\A`/`\z`/`\U`/`\a` — so this is a spec-and-grammar gap, not just a
grammar bug. Flagging so the omission is a deliberate decision rather than an oversight.

**Suggested fix:** If portability is the only criterion, add `\A`, `\z`, `\a`, and the
8-hex `\U........` form to the admitted set (and to design §4.1). If they are deliberately
out of scope (e.g. to keep the subset minimal), say so explicitly in the grammar comment.

---

## design-6 — `(?x)` verbose flag is admitted but the grammar models the body verbosely-incorrectly

**Quote / location:** `flag_chars := value:/[imsxU]+/` (119), used by `inline_flags` (117)
and `flag_group` (111); design §4.1 lists `(?x)` as "portable *as syntax*."

**What's wrong:** The grammar admits the `x` (verbose/extended) flag. Under `x` mode, both
engines (verified to AGREE on the basics) ignore unescaped whitespace in the pattern body
and treat unescaped `#` as a to-end-of-line comment. But the grammar's `literal_char`
(line 216) treats `#` and space as ordinary significant literals, and there is no
flag-sensitive mode switch. So after `(?x)`, the grammar still recognizes the body
char-for-char.

**Why this is lower-stakes but real:** Because the grammar is a pure *recognizer*
(accept/reject only; design §4.3), and because both engines agree on `(?x)` whitespace/`#`
handling for the cases I tested (`(?x)a b c` matches `abc` on both; `(?x)a#c\nb` matches
`ab` on both), this does not by itself produce a portability false-negative on those cases.
But the admission rests on the assumption that `(?x)` is "portable as syntax," which is the
one inline flag whose body *semantics* (whitespace/comment stripping) differ structurally
from non-verbose mode — and `x` interacts with class bodies and `#` in corners I did not
exhaustively diff. Admitting `x` widens the trusted surface for the least-tested-equivalent
flag.

**Consequence:** Possible silent divergence in `(?x)` corners not covered by the design's
ASCII parity cases (§5.6 lists only `(?i)`), and a recognizer that structurally
mis-describes verbose-mode bodies. Lower stakes than design-1/2 because no concrete
divergence was found, but it is an unverified-equivalence admission.

**Suggested fix:** Either (a) drop `x` from `flag_chars` until `(?x)` equivalence is
positively verified and parity-covered, or (b) keep it and add explicit `(?x)` cross-engine
parity cases (including `#` comments and whitespace in classes) to §5.6, and note the
recognizer does not model verbose-mode body rules.

---

## design-7 — Minor: comment claims that don't match the grammar's actual behavior

**Quote / location:**
- Line 207–210 (`literal_char` comment): "Metacharacters (`. * + ? ( ) [ ] { } | ^ $ \`)
  are handled by their own productions above; a bare one here would be a structural token."
  But `{` and `}` have **no** production except inside `bounded` (`{m}`/`{m,}`/`{m,n}`). A
  literal `{`/`}` that is not a valid bound (e.g. `a{`, `a{b}`) is therefore rejected, not
  "handled." (Verified: `a{`, `a{b}` both rejected. Aside: both engines diverge here too —
  Python accepts `a{` as a literal brace, Rust rejects — so rejecting is defensible, but the
  comment misdescribes it.)
- Line 92 `anchor := caret:"^" | dollar:"$"` with the surrounding narrative implying anchors
  are covered — but `\A`/`\z` (design-5) are not, and the comment block at 162–167 lists
  `\b \B` as the only assertions.

**Consequence:** Comments are the spec a future maintainer trusts; these overstate coverage
(`{`/`}` "handled"; metacharacters all have productions) and would mislead someone widening
the grammar. Low stakes (comments only) but worth correcting alongside the substantive
fixes.

**Suggested fix:** Correct the `literal_char` comment to state that bare `{`/`}` are
rejected (only valid bounded quantifiers consume braces), and reconcile the anchor/assertion
comments with whatever design-5 resolves to.

---

## Note on the design's offset/HARD-FAIL claim (informational, not a grammar fault)

The design §5.2 distinguishes "hard fail" (`result is None`) from "short parse"
(`result.pos < len`). Empirically, *whole-pattern* non-portable inputs (`[[:alpha:]]`,
`\p{L}`, `(?=x)`, `\1`, …) ALL return HARD-FAIL (start rule returns `None`), not short
parses — because the left-recursive `alternation` finds no seed. For these,
`longest_parse_len` still pointed at a small but nonzero offset in my probes (e.g. 2 for
`(?P<name>x)`), and at the correct boundary for prefix-portable inputs (`abc[[:alpha:]]` →
4). This is consistent with the design's choice to report `longest_parse_len` rather than
`result.pos`, and is not a grammar defect — recorded here only because the design treats the
short-parse case as common, whereas the dominant observed shape for fully-non-portable
patterns is the hard-fail case (offset still usable). Worth confirming the §7 offset tests
assert against representative *whole-pattern* rejections, not only prefix/tail ones.
