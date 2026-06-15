# Dispositions: adversarial review of `regex.fltkg`

Review under fact-check: `notes-regexfltkg-review.md`.
Artifact revised in place: `regex.fltkg` (companion design corrections in `design.md`).

**Verification method.** Each finding was re-checked by (1) generating the parser from the
draft grammar with the real toolchain
(`uv run python -m fltk.fegen.genparser generate regex.fltkg regex_subset regex_subset_cst`)
and driving `apply__parse_regex` over the disputed corpus, and (2) executing BOTH engines on
each pattern — Python `re` (stdlib, with `FutureWarning` promoted to error) and
`regex_automata::meta::Regex` 0.4 (the exact version in `crates/fltk-parser-core/Cargo.toml`,
via a throwaway Cargo probe, since removed). After applying the fixes, the parser was
regenerated (clean, no GSM validation error) and the full must-accept / must-reject corpus
was re-run; all cases land correctly. The reviewer's "what is correct" summary (clean
generation, whitespace-significance, left-recursion seeds, offset reporting) was confirmed
and is preserved.

---

design-1:
- Disposition: Fixed
- Action: Restructured `char_class` in `regex.fltkg` so negation is an OPTIONAL `^` prefix
  consumed before the body (`%"[" . negated:"^"? . class_body . %"]"`), and `class_body`
  requires a non-empty body (`lead_dash:"-" . items:class_item*` OR `items:class_item+`,
  each with optional trailing `-`). `[^]` is now `[` + `^`(negation) + empty body → reject;
  `[]` is `[` + empty body → reject. Verified: both now SHORT-reject (post-fix corpus),
  matching both engines, which reject `[^]` and `[]` as unterminated sets. The reviewer's
  root cause (PEG fall-through from `negated_class` to `positive_class` letting `^` be an
  ordinary `class_char`) is eliminated because there is no longer a separate positive/negated
  pair to fall through. Added `[]`/`[^]` to the design §4.2 exclusion table and §7
  must-reject corpus. `^` is now allowed as a non-leading literal class member (`[a^b]`,
  `[a^]` — verified portable both engines), so the fix does not over-reject literal carets.
- Severity assessment: High. Over-admission of a both-invalid pattern is the exact
  fail-open failure this lint exists to prevent: the lint would green-light `[^]`, then the
  Rust `all_regex_patterns_compile` test (or Python `re.compile`) would fail later with a
  less-located error, defeating the "reject at generation time with a clear message"
  requirement.

design-2:
- Disposition: Fixed
- Action: Split the class escape/atom grammar. A `class_range` endpoint now draws from
  `class_range_atom` (`class_char_escape | class_char`), where `class_char_escape` admits
  ONLY char-valued escapes (`\\` + `char_escape`: control/hex/unicode/meta) — never a
  shorthand or assertion. `[\d-z]` and `[a-\d]` now SHORT-reject (verified), matching both
  engines, which reject a shorthand as a range endpoint. While fixing this I found and closed
  an ADJACENT over-admission the review did not name: the draft's shared `escape` let a class
  MEMBER be `\b`/`\B` (`assertion`), so `[\b]`/`[\B]` were accepted — but `[\b]` is backspace
  on Python yet REJECTED by Rust (divergent), and `[\A]`/`[\z]` are rejected by both. The new
  `class_member`/`class_escape` path excludes assertions and anchors entirely (class escapes =
  `class_shorthand | char_escape`), so `[\b]`, `[\B]`, `[\A]`, `[\z]` now reject (verified).
  Plain shorthand members (`[\d]`, `[\w\s]`) and escape range endpoints (`[\n-\r]`,
  `[\x41-\x5a]`) remain accepted (verified portable). Added all these to design §4.1/§4.2/§7.
- Severity assessment: High. Same fail-open class as design-1 — a both-invalid (`[\d-z]`) or
  Rust-rejected (`[\b]`) construct passing the allowlist re-surfaces later as an opaque
  `regex-automata` compile error instead of the located generation-time rejection required.

design-3:
- Disposition: Fixed (with one deliberate, source-justified partial exclusion)
- Action: Added optional `lead_dash:"-"?`/`trail_dash:"-"?` markers in `char_class`, and a
  `lead_dash`-first `class_body` alternative so a dash-only class (`[-]`) is admitted. The
  common leading/trailing-dash idioms now ACCEPT (verified both engines, no `FutureWarning`):
  `[-a]`, `[a-]`, `[a-z-]`, `[+\-]`, `[-]`. The INTERIOR literal dash between two members
  (`[a-z-0]`) is deliberately left REJECTED: `class_char` still excludes `-`, so an interior
  `-` not part of a range has no production. Rationale for the partial exclusion is recorded
  in the grammar comment and design §4.2: an interior `member - member` dash is the exact
  shape of the `--` set-difference operator (an explicitly-excluded divergent construct,
  design §4.2). Python `re` flags `[--a]`/`[+--]`/`[a-z--_]` with `FutureWarning: Possible
  set difference` (verified) — a signalled future-divergence risk — whereas `[a-z-0]` itself
  does not warn. Admitting interior dashes broadly risks letting a `--` look-alike through;
  rejecting them is a safe over-rejection consistent with the grammar's fail-closed default.
  The common cases the reviewer cited (`[+\-]`, `[a-z-]`, `[-a]`) are all covered. Added
  must-accept dash cases and the `[a-z-0]` deliberate-reject to design §7.
- Severity assessment: Medium. Over-rejection is the safe direction (loud build error, not
  silent mis-parse), but literal dashes in classes are common enough that the leading/trailing
  cases would bite real grammars; those are now accepted. The residual interior-dash rejection
  is the conservative choice that keeps the `--` set-op door closed.

design-4:
- Disposition: Fixed
- Action: Made `alternation` admit an empty branch (`branch:concatenation?`) and the
  left-recursive growth admit an empty right operand (`right:concatenation?`). Group bodies
  are `body:alternation`, so `()`/`(?:)` inherit the empty-branch capability. `()`, `(?:)`,
  `a|`, `|a`, `a||b` now ACCEPT (verified), matching both engines (empty branch = empty-match
  alternative). The reviewer flagged the interaction with FLTK's no-repeated-nilable-item
  validator (`gsm.py:418-453`); I verified the concern is handled: the parser REGENERATED
  CLEANLY after the change (no GSM validation error). Nilability is confined to the optional
  `concatenation?` base case rather than a `+`/`*` over a nilable term — the growth
  alternatives consume a `|` or a `repetition`, and `repetition`'s `atom` is non-nilable — so
  the no-repeated-nil check is satisfied. Documented the nilable-design reasoning in the
  grammar `alternation` comment and added the cases to design §4.1/§7.
- Severity assessment: Medium. Over-rejection (safe direction) of valid portable grammars
  using an empty group or empty alternative (e.g. `(foo|)` for "optional foo"); a real
  completeness gap not covered by the in-tree corpus, now closed.

design-5:
- Disposition: Fixed
- Action: Added the genuinely-portable escapes. New `anchor_escape := /[Az]/` admits `\A`/`\z`
  at top level (added to `escape_body`); `control_escape` extended to `[nrtfv0a]` to admit
  `\a` (bell); `unicode_escape` now has an 8-hex `\UHHHHHHHH` alternative alongside the 4-hex
  `\uHHHH`. `\A`, `\z`, `\a`, `\U00000041` now ACCEPT (verified portable both engines). Per
  the per-context verification, `\A`/`\z` are admitted ONLY at top level — `[\A]`/`[\z]` are
  rejected by both engines, so they are NOT in any class-escape path (this dovetails with the
  design-2 class/top-level escape split). The reviewer's "correctly excluded for the record"
  set was re-verified and remains excluded: `\Z` (Python OK, Rust ERR), braced `\x{..}`/`\u{..}`
  (Rust OK, Python ERR), `\07` octal (Python OK, Rust ERR). Updated design §4.1 admitted-escape
  list and §4.2 exclusion table.
- Severity assessment: Medium. Over-rejection (safe) of common portable anchors (`\A`/`\z`
  especially are standard); spurious Rust build failures for grammars using them, now avoided.

design-6:
- Disposition: Fixed
- Action: Removed `x` from `flag_chars` (now `/[imsU]+/`), so the `(?x)` verbose/extended flag
  is no longer admitted by `inline_flags` or `flag_group`. `(?x)a b` now SHORT-rejects
  (verified). Rationale (grammar comment + design §4.1): the grammar is a pure recognizer that
  models the body char-for-char with no flag-sensitive mode switch, so under `x` (which strips
  unescaped whitespace and treats `#` as a comment) it cannot faithfully recognize a
  verbose-mode body; `x` is the one inline flag whose body rules differ structurally, and its
  corner-case cross-engine equivalence (`#` comments, whitespace in classes) was not verified.
  This is the fail-closed choice the reviewer's option (a) recommended; chose Fixed over TODO
  because the change is a one-character grammar edit and aligns with the grammar's stated
  fail-closed default. Design §4.1/§5.6 note the path to re-admit (positive `(?x)` parity
  coverage + a verbose-aware body model). The other flags (`i`,`m`,`s`,`U`) remain admitted.
- Severity assessment: Medium. Lower-stakes than design-1/2 (no concrete divergence was found),
  but admitting `x` widened the trusted surface for the least-verified-equivalent flag with a
  structurally-unmodeled body. Excluding it is the conservative, silent-divergence-safe move;
  the cost is over-rejection of `(?x)` grammars, which is the safe direction.

design-7:
- Disposition: Fixed
- Action: Corrected the grammar comments AND fixed a real over-rejection the comment masked.
  (a) `literal_char` previously excluded `]` and `}`; both are portable bare literals on both
  engines (`a]b`, `a}b`, `]`, `}` all OK — verified), so they were being over-rejected, not
  merely "handled by other productions." `literal_char` is now `/[^.*+?()\[|^$\\{\n]/` —
  excluding only the structural OPENERS `[` and `{` plus the metacharacters with their own
  productions, and ADMITTING the closers `]`/`}`. The grammar comment now states accurately
  that `]`/`}` are admitted literals and that bare `{` is excluded because Rust rejects `a{`
  (divergent; Python accepts it). This also fixes the design's own §7 false-positive guard
  `[\[:alpha:]]`, which the draft SHORT-rejected on its trailing bare `]` and now ACCEPTs
  (verified). (b) Reconciled the anchor/assertion comments with design-5 (top-level `\A`/`\z`
  now present; class escapes exclude assertions/anchors). Updated design §4.1/§7 accordingly.
- Severity assessment: Low-to-medium. The reviewer scored this as comment-only, but the
  underlying `]`/`}` exclusion was a genuine over-rejection (and broke a design test fixture).
  Fixing both the comment and the production removes a real spurious-rejection surface;
  keeping `{` excluded preserves correct rejection of the divergent bare-brace case.

---

## Informational note (not a finding)

The reviewer's closing note on offset/HARD-FAIL shapes was re-confirmed against the revised
grammar: fully-non-portable whole-pattern inputs return HARD-FAIL (start rule `None`) with a
small nonzero `longest_parse_len` (e.g. `\p{L}` → 1, `(?=x)` → 2), and prefix-portable
inputs report the boundary. The design's choice to report `error_tracker.longest_parse_len`
rather than `result.pos` (§5.2) remains correct and is unchanged. No grammar action needed.
The design's §7 offset assertions should include representative whole-pattern rejections, not
only prefix/tail ones (already implied by the §7 reject corpus, which is whole-pattern).
