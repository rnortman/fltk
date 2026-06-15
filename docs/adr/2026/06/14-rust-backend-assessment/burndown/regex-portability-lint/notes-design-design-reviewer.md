# Design review: `regex-portability-lint`

Reviewer: design-reviewer. Base commit 205c36b. Adversarial fact-check of
`design.md` against source, exploration, and the spec (recommended-actions.md +
recommended-actions-eli5.md, slug `regex-portability-lint`).

Verification summary: nearly all load-bearing claims check out against source.
Verified accurate: `_regex_idx` location/dedup (`gsm2parser_rs.py:136-141`);
CLI handler `except (ValueError, RuntimeError, NotImplementedError)` at
`genparser.py:389-391`; `generate()` reaches `_regex_idx` via `_gen_rule` inside
the try block; Python regex site `terminalsrc.py:177-181`; `gsm.py:151-172`
Regex/`_test_regex_empty`; Rust `consume_regex` + `Input/Anchored` imports
(`terminalsrc.rs:1-9,141-166`); `pub use regex_automata` at `lib.rs:23`; Cargo
dep `Cargo.toml:17-27`; `all_regex_patterns_compile` emission
(`gsm2parser_rs.py:976-996`); ADR `06/10-rust-parser-codegen/README.md` Status:
Accepted (immutable); parity helpers `run_parity_corpus_entry`/`assert_cst_equal`
exist (`tests/parser_parity.py:151,10`); fixture corpus wiring
(`test_rust_parser_parity_fixture.py:20,135-139`); a2-parity claims at
`a2-parity.md:75-122` match the design's restatement. The two-option weighing
(§2) and the recommendation/decision-gate framing (§3, §9 O1) honestly engage the
STATUS "this OR better" requirement and ground Option B's infeasibility in the
exploration. Findings below are gaps/imprecisions, not invalidations.

---

## design-1: Lint insertion point also receives the hardcoded trivia `\s+`; design never says so

- **Section:** §4.2 "Wire into the Rust generator at `_regex_idx`"; §4.1; §1
  (which asserts "the danger is entirely in **user-grammar regexes**").
- **What's wrong:** The design places the lint inside `_regex_idx` and frames it
  throughout as protecting *user-grammar* regexes. But `_regex_idx` is called from
  TWO sites: the user `gsm.Regex` term at `gsm2parser_rs.py:758`
  (`self._regex_idx(term.value)`) AND the hardcoded trivia whitespace pattern at
  `gsm2parser_rs.py:578` (`ws_idx = self._regex_idx(r"\s+")`). A lint placed inside
  `_regex_idx` will scan `\s+` on every grammar that emits a WS_ALLOWED/WS_REQUIRED
  separator. The design never acknowledges that the trivia pattern flows through
  the chosen chokepoint.
- **Why:** `gsm2parser_rs.py:577-578` registers the literal `\s+` via `_regex_idx`;
  this is generator-internal, not author-controlled. Source confirmed.
- **Consequence:** Benign today — `\s+` passes the §4.1 denylist (verified: neither
  the POSIX regex `\[\[:\^?[a-z]+:\]\]` nor `\\[pP]\{` matches `\s+`), so no false
  rejection now. But the design's reasoning ("fires only for user-grammar regexes",
  §1/§4.2) is inaccurate at the chosen insertion point, and a future denylist
  addition that happens to match `\s+` (e.g. an over-broad `\s`/`\w` non-ASCII rule
  from §5/O4) would reject *every grammar with whitespace separators* — a
  self-inflicted breakage with a confusing error naming an internal pattern the
  author never wrote. The implementer should either lint only at the user-term call
  site (`:758`) rather than inside `_regex_idx`, or explicitly carve out the
  generator-internal trivia pattern and document why.
- **Suggested fix:** Move the `scan_regex_portability` call to the `gsm.Regex`
  branch in `_gen_consume_term` (`:757-761`) instead of `_regex_idx`, OR state in
  §4.2 that the trivia `\s+` also transits `_regex_idx` and is known-clean, and add
  a test pinning that the trivia pattern is never flagged.

## design-2: §4.1 POSIX detection regex differs from exploration's and the divergence is unexplained

- **Section:** §4.1 detection table, POSIX row: pattern `\[\[:\^?[a-z]+:\]\]`.
- **What's wrong:** The exploration (`exploration.md:200`, and a2-parity framing)
  proposes `\[\[:[a-z]+:\]\]`. The design silently changes it to add `\^?` (to
  catch negated `[[:^alpha:]]`). The `\^?` addition is correct and is an
  improvement — `[[:^alpha:]]` is a real POSIX-negation form and §6 even tests
  `[[:^alpha:]]`. But the design presents the regex as if it were the exploration's
  without noting the change or why, and the `\^?` sits between `:` and the class
  name, which is the correct position only for the `[[:^name:]]` form.
- **Why:** exploration.md:200 vs design.md:225; both are in-repo.
- **Consequence:** Low — the design's regex is actually the better one. The risk is
  only that an implementer cross-referencing the exploration sees two different
  patterns with no note and picks the weaker one (missing negated POSIX classes
  that §6 explicitly requires to be flagged). Calling out the deliberate refinement
  avoids that.
- **Suggested fix:** Note in §4.1 that the POSIX detector intentionally extends the
  exploration's regex with `\^?` to cover `[[:^class:]]`.

## design-3: §4.1 "bare `\p{L}` short form" parenthetical is redundant/misleading

- **Section:** §4.1 Unicode-property row: detection `\\[pP]\{` "(and bare `\p{L}`
  short form)".
- **What's wrong:** `\p{L}` is not a distinct "short form" relative to `\\[pP]\{`
  — it already begins with `\p{`, so `\\[pP]\{` matches it. The genuinely distinct
  short form the parenthetical seems to gesture at is `\pL` (single-letter class,
  no braces), which `\\[pP]\{` does NOT match. The design either misnames the case
  or omits the real gap.
- **Why:** Python `re` and regex-syntax both accept `\pL` as shorthand for `\p{L}`;
  the design's detector regex requires the `{`. design.md:226 self-contradicts (the
  detection column requires `\{`; the note claims it also covers a "bare" form).
- **Consequence:** If `\pL`/`\PN` brace-less property shorthands are a real
  divergence vector, they slip the lint as a false negative — exactly the class of
  silent divergence (Unicode property) the item exists to close. If they are not a
  concern, the parenthetical is noise that will mislead the implementer into
  thinking they are covered. Either way the design is internally inconsistent on
  this row.
- **Suggested fix:** Decide: either extend the detector to `\\[pP](\{|[A-Za-z])`
  and list `\pL` in the §6 tests, or drop the "bare short form" parenthetical and
  state brace-less `\p` shorthand is out of scope (with rationale).

## design-4: §4.3/§9-O3 escape hatch undercuts the fail-closed contract and the gencode-drift-gate

- **Section:** §4.3 "Escape hatch" + §9 O3 (`--allow-nonportable-regex` generator
  flag, recommended).
- **What's wrong:** The recommended escape hatch is a CLI flag on `gen-rust-parser`
  that downgrades the rejection to a warning. The design argues this keeps the
  opt-out "auditable at the build invocation." But the committed Rust parsers are
  regenerated via the `Makefile` (`make gencode`, lines 226/280), and the sibling
  Phase-A item `gencode-drift-gate` (recommended-actions.md:42-58) regenerates and
  `git diff --exit-code`s the committed output. A flag-based opt-out lives in the
  Makefile invocation, not in the grammar — so the audit trail for "this grammar
  intentionally uses a non-portable construct" is in a build script, divorced from
  the `.fltkg` it applies to, and per-pattern granularity is lost (the flag is
  whole-invocation: it disables the lint for *every* pattern in that grammar).
- **Why:** Makefile:226,280 show per-grammar invocations; an `--allow-nonportable-regex`
  flag there suppresses all flagged patterns for that whole grammar. The spec only
  asks to "reject them with a clear error message" (eli5 doc) — it does not request
  an escape hatch at all.
- **Consequence:** The flag re-opens the exact silent-divergence hole the item
  closes, but at whole-grammar granularity and with the opt-out recorded far from
  the offending pattern. A consumer who adds the flag to silence one deliberate
  `[[:alpha:]]` also silences any *accidental* future non-portable construct in the
  same grammar — re-creating silent divergence under a green build. This is broader
  than the spec asks for (scope creep: the spec wants rejection, not a bypass) and
  weaker than the per-pattern, in-grammar opt-out the design itself calls for in its
  own framing. Note the design does flag this as an open question (O3 lists "no
  escape hatch" as an option), so this is a recommendation-quality concern, not a
  hidden defect.
- **Suggested fix:** Lean toward O3's "no escape hatch" default for the first ship
  (simplest, matches the spec, preserves fail-closed). If an opt-out is truly
  needed, prefer a per-pattern in-grammar mechanism so the audit lives with the
  pattern and granularity is one-pattern — but the design itself calls an in-pattern
  sentinel "brittle," so the honest conclusion is: ship with no hatch, add one only
  on demonstrated need (consistent with the project's TODO/"concrete need" posture).

## design-5: §4.5 parity-corpus addition risks `_test_regex_empty` interaction not analyzed

- **Section:** §4.5 (add `(?i)` on pure-ASCII, anchors `^a.b$`, etc.) + §5 "Empty /
  trivial patterns" claim that emptiness testing is "unchanged".
- **What's wrong:** §4.5 proposes adding parity rules including anchors and `(?i)`.
  `gsm.Regex.can_be_nil`/`_test_regex_empty` (`gsm.py:165-172`) compiles each
  pattern with `re.compile` and tests `.match("")` to decide nil-ability, which
  feeds grammar-validation (left-recursion / quantifier-on-nullable checks). The
  design asserts the lint "does not touch emptiness testing" (true), but does not
  check that the *new fixture patterns* it adds are non-nullable where the grammar
  rules using them assume non-nullability (e.g. `item:atom+` requires atom
  non-nil). A pattern like `(?i)abc` is non-nil, but an anchor-only or `x*`-style
  addition could be nil and trip unrelated grammar validation, failing fixture
  generation for reasons unrelated to portability.
- **Why:** gsm.py:156-172 shows can_be_nil is consulted during grammar processing;
  fixture rules like `items := item:atom+` (rust_parser_fixture.fltkg:22) depend on
  non-nullable operands.
- **Consequence:** A carelessly chosen "portable-but-tricky" fixture pattern could
  fail fixture *generation* (nil-operand validation) rather than demonstrate parity,
  producing a confusing red that looks like a lint/parity bug. Low severity (caught
  immediately at fixture build), but worth a one-line constraint in §4.5 that added
  patterns be non-nullable / used in rules that tolerate nullability.
- **Suggested fix:** In §4.5, state that added parity patterns must be non-nullable
  (or placed in rules that permit nil operands) so they exercise parity, not the
  nil-validation path.

## design-6: §6 "no committed grammar trips the lint" verified TRUE, but the near-miss deserves a note

- **Section:** §6 / §7 ("none expected"; regen-and-confirm verification step).
- **What's wrong:** Not wrong — verified correct, but the design omits a relevant
  fact an implementer will hit. `fltk/fegen/fltk.fltkg:76` and `bootstrap.fltkg:21`
  contain a negative-lookahead block-comment regex
  `/[^*]*(?:\*(?!\/)[^*]*)*/` — a construct the §4.1 denylist flags (lookahead).
  These grammars are NOT compiled to committed Rust parsers (the committed Rust
  parser comes from `fegen.fltkg`, Makefile:231/278, whose block_comment uses the
  lookahead-free `(?:[^*]|\*+[^\/\*])*` — confirmed in
  `crates/fegen-rust/src/parser.rs:25` REGEX_PATTERNS). So the lint never sees the
  lookahead pattern and §6's claim holds. But `fltk.fltkg` is described in-repo as
  "intentionally broken" (Makefile:249); an implementer who tries to gen-rust-parser
  it as a test will (correctly) hit the lint and may misread it as a regression.
- **Why:** Verified by grep across all `*.fltkg` and by reading the committed
  REGEX_PATTERNS arrays; Makefile:231,249,278.
- **Consequence:** None to correctness — the design's "none expected" is accurate
  for committed Rust targets. The value of recording it: it both (a) confirms the
  design's no-regression claim against the one real in-tree lookahead, and (b)
  gives the §6 regen-verification step a known data point (don't run the lint
  against `fltk.fltkg`/`bootstrap.fltkg` and call a flag a finding).
- **Suggested fix:** Add a sentence to §6 noting the lookahead in
  `fltk.fltkg`/`bootstrap.fltkg` is expected to flag if ever Rust-generated, and is
  not a committed Rust target, so it is out of scope for the regen-confirm step.

---

No groundedness failures found in the recommendation logic. No scope-discipline
problems beyond design-4 (escape hatch is the one place the design proposes more
than the spec asks). Requirements coverage (reject non-portable constructs at
gen time + reword docstring as hard boundary + expand parity corpus) is fully
mapped to §4.2 / §4.4(1) / §4.5 respectively, and the §3 decision legitimately
weighs the STATUS's "OR better" option per the requirement.
