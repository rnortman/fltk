# Design: `regex-portability-lint`

**Burndown item:** `regex-portability-lint` (Phase B, step 6; assessment finding
`a2-parity:posix-class-divergence`).

**Mode:** skip-requirements. Requirements are taken from
`docs/adr/2026/06/14-rust-backend-assessment/recommended-actions-eli5.md` and
`recommended-actions.md` (slug `regex-portability-lint`); exploration from
`burndown/regex-portability-lint/exploration.md`. This design does not restate those —
it refers to them.

**Design-gate history.** An earlier draft of this design recommended a generation-time,
hand-written **denylist** detector (a Python module that scanned each pattern string for
known-bad substrings with `re`). The user reviewed it and redirected
(`notes-design-user.md`):

> Why not create an FLTK *grammar* of the supported regexes, and actually parse the regex
> using a generated FLTK parser. Otherwise we're basically building a janky (and probably
> unreliable) regex-based parser inside a parser generation library, which seems like we
> don't trust our own product.

This design adopts that directive. The validator is now an FLTK grammar of the portable
regex subset, compiled by FLTK's own generator into a committed Python parser, and run over
each grammar regex at Rust-parser generation time. The directive was evaluated against the
codebase and found feasible with no blocker (§3); the disposition record is
`dispositions-design-user.md`.

§1 establishes the problem. §2 states the approach. §3 records the feasibility finding. §4
specifies the regex-subset grammar. §5 specifies the wiring. §6–§10 cover edge cases,
tests, files, non-goals, and open questions.

---

## 1. Root cause / context

FLTK has two parser backends that run **two different regex engines** against the same
grammar-authored pattern strings:

- Python backend: `re.compile(regex).match(self.terminals, pos=pos)`
  (`fltk/fegen/pyrt/terminalsrc.py:177-181`). Python's stdlib `re`.
- Rust backend: `regex_automata::meta::Regex` via `consume_regex`
  (`crates/fltk-parser-core/src/terminalsrc.rs:141-166`); the engine is declared at
  `crates/fltk-parser-core/Cargo.toml:17-27`.

A grammar regex enters the system as raw text between `/.../` delimiters
(`fltk/fegen/fegen.fltkg:13,17`), is stored verbatim as `gsm.Regex.value`
(`fltk/fegen/fltk2gsm.py:168-170`, `fltk/fegen/gsm.py:151-172`), and is emitted verbatim
into the Rust parser's `REGEX_PATTERNS` table (`fltk/fegen/gsm2parser_rs.py:291-321`).
No portability validation happens anywhere in this path.

The only existing guard is the generated `#[cfg(test)] fn all_regex_patterns_compile`
(`gsm2parser_rs.py:976-996`), which calls `regex_automata::meta::Regex::new(pat)` per
pattern under `cargo test`. It catches constructs the Rust engine **rejects at compile
time** — lookahead, lookbehind, backreferences. It is documented as enforcing "the common
subset" at `gsm2parser_rs.py:6-15` and `docs/adr/2026/06/10-rust-parser-codegen/README.md:48-60`.

The gap is **silent semantic divergence**: constructs that *compile cleanly on both
engines* but *match differently at runtime*. The assessment verified this by direct
execution (`docs/adr/2026/06/14-rust-backend-assessment/a2-parity.md:75-122`):

- `[[:alpha:]]`: `regex-automata` treats it as the POSIX alpha class (matches any letter);
  Python `re` parses it as a malformed nested set and matches **nothing** (emitting a
  `FutureWarning`). A rule `word := value:/[[:alpha:]]+/` parses `"hello"` on Rust and
  fails entirely on Python — same grammar, same input, opposite parse tree, no error on
  either side. `[[:digit:]]`, `[[:space:]]`, `[[:alnum:]]` behave the same way.
- More broadly the two engines also differ on `(?i)` case-folding tables, `\p{...}`
  Unicode property classes, and the exact `\d`/`\w`/`\s` Unicode tables (each tied to its
  engine's Unicode DB version). The assessment confirmed the POSIX case by execution and
  flags the others as the same class of risk.
- The one pattern both backends actually share — the hardcoded trivia `\s+` — was verified
  to agree across 10 representative whitespace codepoints (`a2-parity.md:101-104`), so the
  trivia path is safe; the danger is in **user-grammar regexes**.

Why this matters for FLTK specifically (CLAUDE.md, "Generated Output is Public API"): the
grammar regex surface is the primary place an out-of-tree consumer's grammar meets the
engine boundary, and it is the least-defended. A consumer whose Python-backed grammar uses
a POSIX class can switch to the Rust backend and get a different parse tree with no error
and no failing test — a direct violation of the near-drop-in contract.

---

## 2. Approach: validate each grammar regex against an FLTK grammar of the portable subset

Author an FLTK grammar, `regex_subset.fltkg`, whose subject language is **the portable
regex subset** — exactly the regex constructs that behave identically on Python `re` and
`regex-automata`. Generate a Python parser + CST from it with the existing
`genparser generate` pipeline and **commit the generated artifacts**, the same way the
`unparsefmt`, `toy`, and `fegen` parsers are generated and committed
(`Makefile:247-297`). At Rust-parser generation time, validate each author-written grammar
regex by **parsing it with that generated parser**:

- If the regex-subset parser consumes the entire pattern, the pattern is in the portable
  subset → accept.
- If it stops short (does not reach end of input), the pattern contains a construct outside
  the portable subset → reject with a clear, located error naming the pattern and the
  furthest-progress offset where parsing failed (§5.2).

This is an **allowlist** (parse-the-known-good-subset), not a denylist (scan-for-known-bad).
That inversion is the substance of the design and the reason it answers the directive:

- **Fail-closed, not fail-open.** A denylist accepts any construct nobody remembered to
  enumerate; a divergent construct not on the list passes silently — re-opening the exact
  hole this item exists to close. The subset grammar accepts only what it explicitly
  admits; an unrecognized construct is rejected by default. For the project's stakes
  (out-of-tree grammars are public API), fail-closed is the correct default.
- **The supported subset is one readable, version-controlled artifact** (`regex_subset.fltkg`),
  not a scatter of denylist regexes with escaping caveats. It doubles as the executable
  definition the `document-scope-boundary` item points at (§5.4).
- **It dogfoods FLTK.** The validator *is* an FLTK-generated parser, which is the
  directive's core point: a parser-generation library should validate its inputs with a
  generated parser, not a hand-rolled string scanner.

The constructs the assessment verified as divergent or unsupported — POSIX classes,
`\p{...}`/`\P{...}`, nested set operations (`&&`, `--`), lookaround, backreferences — are
all **syntactically distinguishable** from the portable subset, so they are simply absent
from `regex_subset.fltkg` and the parser rejects them by construction. No special-casing per
divergent construct is required; they fall out of the grammar's coverage.

---

## 3. Feasibility (directive evaluated against the codebase; no blocker)

Every load-bearing precondition was checked against the actual code:

1. **A committed generated FLTK parser is pure Python and is the supported reuse pattern.**
   `fltk/unparse/unparsefmt_parser.py` is a committed, generator-produced parser the
   production path imports and instantiates (`fltk/plumbing.py:29,350`;
   `fltk/unparse/genunparser.py:15,65`). Its only imports are `fltk.fegen.pyrt.*` and its
   sibling CST module (`unparsefmt_parser.py:1-8`) — **no Rust extension, no build step, no
   bootstrapping cycle at lint time.** `regex_subset_parser.py` will have the identical
   shape and be importable the same way. Critically, the validator runs entirely on the
   Python backend, so generating a *Rust* parser does not require the Rust extension to be
   built first to validate its regexes.

2. **FLTK already self-hosts grammars-of-grammars.** `fegen.fltkg` and `bootstrap.fltkg`
   are FLTK grammars whose subject language is FLTK grammar syntax; the committed
   `fltk_parser.py` is generated from `fegen.fltkg` (`Makefile:250-252`). A grammar whose
   subject language is regex syntax is the same move one level over — squarely within
   precedent.

3. **Regex syntax is comfortably expressible in `.fltkg`.** Regex is a textbook PEG/CFG
   language: concatenation, alternation (`|`), quantifiers (`?`/`+`/`*`), grouping,
   character classes, escapes, anchors. The `.fltkg` format supplies all of these
   (`fegen.fltkg:1-21`: alternatives, three quantifiers, sub-expressions, labels, literals,
   regex terminals). FLTK additionally **supports left recursion** (direct and
   indirect/mutual) via a packrat seed-growing memoizer (`fltk-grammar-reference.md` §9.1;
   `memo.py:82-257`), so the grammar may be written with whatever recursion direction reads
   most naturally — a left-recursive `alternation`/`concatenation` stratification, exactly
   the shape `fegen.fltkg`'s own `alternatives`/`items` rules use. The one structural
   obligation is that any left-recursive rule include a non-left-recursive base-case
   alternative (`fltk-grammar-reference.md` §9.2; `memo.py:104-106, 147-149`), which the
   regex stratification supplies naturally (the base of `concatenation` is a single
   `repetition`, the base of `repetition` is an `atom`).

4. **The validator's own terminals are safe.** `regex_subset.fltkg`'s leaf matchers (the
   character-class and escape recognizers) are themselves FLTK regexes that run on Python
   `re`. These are simple, fixed, hand-audited classes (`[a-z0-9]`, `\\.`, etc.), **not
   user-supplied**, so the regex-engine-divergence problem does not recurse into the
   validator: we are not asking the validator's regexes to be cross-engine portable, only
   to correctly recognize the structure of the user's pattern string under Python `re`,
   which is the only engine the validator ever runs on.

5. **The error path already exists, unchanged.** The Rust generator's `gsm.Regex` term site
   raises `ValueError`; `genparser gen-rust-parser` converts that to `typer.Exit(1)` with
   the message (`genparser.py:386-391`). The validator plugs into that exact site and reuses
   the path verbatim.

**The one honest limit (unchanged from any static approach).** A grammar validates
*syntactic membership* in the portable subset; it cannot detect *same-syntax /
different-semantics* divergence — `\d`/`\w`/`\s`, `\b`/`\B` (which are defined in terms of
`\w`), and `(?i)`, all over non-ASCII, where the divergence is driven by Unicode-DB version
on identical syntax (`exploration.md:320-328`; the full ledger is §6). The subset grammar
admits these syntaxes (they are portable for ASCII and excluding them would over-reject), so
this residual is documented-only, exactly as a denylist would also have to leave it (§6, §10
O2). This is a limit of *all* static checkers, not a deficiency of the grammar approach.

Conclusion: feasible, strictly safer than the denylist, no blocker.

---

## 4. The regex-subset grammar (`fltk/fegen/regex_subset.fltkg`)

A new FLTK grammar describing the portable subset. It is a **recognizer**: the CST it
produces is not consumed structurally; only "did it parse to end of input?" matters
(§5.2). The grammar must therefore be complete enough to accept the portable constructs
real grammars use, and exclude the divergent/unsupported ones.

### 4.1 Constructs the grammar admits (portable)

Scoped to what the existing in-tree fixtures and parity corpus exercise
(`rust_parser_fixture.fltkg`: `[0-9]+`, `[a-z]+`, `[À-ÿ]+`, `[!@#$]+`,
`/([^\/\n\\]|\\.)+/` in `fegen.fltkg`, etc.) plus the common portable set. Every
admit/reject decision below was verified by executing **both** engines (Python `re` and
`regex_automata::meta::Regex` 0.4); a construct is admitted only if both engines accept it
and agree, and excluded if either rejects it or the two disagree.

- **Literals:** ordinary characters (anything that is not a structural regex
  metacharacter). The bare *closers* `]` and `}` **are** admitted as literals (a bare
  `]`/`}` outside a class is a portable literal on both engines: `a]b`, `a}b`, `]`, `}`).
  A bare `{` is **not** a literal (Rust rejects `a{`, Python accepts it — divergent), so
  `{` is admitted only as the opener of a valid bounded quantifier.
- **Escapes (top level):** `\\` followed by a portable shorthand, assertion, anchor,
  char escape, or escaped metacharacter. Admitted: class shorthands `\d \D \w \W \s \S`;
  word-boundary assertions `\b \B`; the text anchors `\A` and `\z`; control escapes
  `\n \r \t \f \v \0 \a` (`\a` = bell, portable both engines); escaped metacharacters
  (`\. \* \+ \? \( \) \[ \] \{ \} \| \^ \$ \/ \\ \-`); and the numeric escapes `\xHH`,
  `\uHHHH` (4-hex) and `\UHHHHHHHH` (8-hex) — all verified portable. The class shorthands
  `\d`/`\w`/`\s` (with negations) and the assertions `\b`/`\B` are admitted as
  ASCII-portable but carry a non-ASCII semantic residual (the documented limit, §6).
  **Not** admitted: `\p`/`\P` (Unicode property — divergent), `\1`–`\9` / `\k`-style
  backreferences (unsupported), `\Z` (Python accepts, Rust rejects — divergent), the
  braced `\x{..}`/`\u{..}` forms (Rust accepts, Python rejects), and `\07` octal (Python
  accepts, Rust rejects).
- **Character classes:** `[ ... ]` and negated `[^ ... ]`. The negation `^` is an
  optional prefix, not a member, so `[^]` (empty negated) and `[]` (empty positive) are
  both **rejected** — both engines reject them. A class body is a non-empty sequence of
  single chars, **class escapes**, and ranges `a-z`. A literal `-` is admitted only in
  the unambiguous leading/trailing positions (`[-a]`, `[a-]`, `[a-z-]`, `[+\-]`, `[-]` —
  verified portable, no `FutureWarning`); an **interior** literal `-` between two members
  (`[a-z-0]`) is deliberately **rejected**, because it is the shape of the `--`
  set-difference operator (Python flags it `FutureWarning`; see §4.2). **Class escapes
  are a strict subset of top-level escapes:** the assertions `\b`/`\B` and the anchors
  `\A`/`\z` are **excluded inside a class** (`[\b]` = backspace on Python but rejected by
  Rust — divergent; `[\A]`/`[\z]` rejected by both). A **range endpoint** must be a
  single char or char-valued escape, never a shorthand (`[\d-z]`/`[a-\d]` are rejected by
  both engines). **Not** admitted inside a class: the nested POSIX form `[:name:]`, the
  set-operation tokens `&&` / `--`, and a nested `[`.
- **Anchors:** `^` and `$` (plus the `\A`/`\z` anchor escapes, top level only).
- **Quantifiers:** `?`, `*`, `+`, and bounded `{m}` / `{m,}` / `{m,n}`, each optionally
  followed by a lazy `?`.
- **Groups:** capturing `( ... )`, non-capturing `(?: ... )`, and flag-scoped
  `(?flags: ... )`. Group bodies may be **empty** (`()`, `(?:)` — both engines accept the
  empty match). **Not** admitted: lookaround group prefixes `(?=` `(?!` `(?<=` `(?<!`,
  named-group `(?P<name>`/reference `(?P=`, and the flag-negation forms `(?-i)` / `(?i-s:)`
  (`(?-i)` diverges — Python rejects, Rust accepts).
- **Inline flags:** `(?i)`, `(?m)`, `(?s)`, `(?U)` and combinations (portable *as syntax*;
  the non-ASCII `(?i)` semantic residual is the documented limit, §6). The `(?x)`
  verbose/extended flag is **excluded**: `x` changes body semantics (strips unescaped
  whitespace, treats `#` as a comment) but this recognizer models the body char-for-char
  with no flag-sensitive mode switch, so it cannot faithfully recognize a verbose body;
  admitting it would trust the one inline flag whose body rules differ structurally, with
  no cross-engine equivalence verified for its corners. Excluded fail-closed; re-admit
  only with positive `(?x)` parity coverage (§5.6) and a verbose-aware body model.
- **Alternation:** `A | B | ...`, including **empty branches** (`a|`, `|a`, `a||b` — the
  empty branch is the empty-match alternative, accepted by both engines).

### 4.2 Constructs the grammar excludes (rejected by absence)

Each maps to a verified or known divergence/unsupported class
(`a2-parity.md:83-100`, `exploration.md:184-198`):

| Excluded construct | Example | Why excluded |
|--------------------|---------|--------------|
| POSIX class | `[[:alpha:]]`, `[[:^digit:]]` | Silent: Rust = POSIX class, Python `re` = match-nothing (verified) |
| Unicode property | `\p{L}`, `\P{N}`, `\pL` | `regex-automata` accepts; Python `re` rejects `\p`/`\P` (verified) |
| Set operations | `[a-z&&[^aeiou]]`, `[\w--_]` | Rust set ops; Python `re` has no equivalent. Interior literal `-` (`[a-z-0]`) is also excluded as a `--` look-alike (Python `FutureWarning`) |
| Lookahead/behind | `(?=x)` `(?!x)` `(?<=x)` `(?<!x)` | Rust rejects at compile; rejected earlier with clearer message |
| Backreferences / named groups | `\1`, `(?P=name)`, `(?P<name>x)` | Rust rejects (backrefs) / divergent group syntax; rejected earlier |
| Empty class | `[]`, `[^]` | Both engines reject (unterminated set) — verified |
| Class assertion/anchor | `[\b]`, `[\B]`, `[\A]`, `[\z]` | `[\b]` = backspace on Python but rejected by Rust (divergent); `[\A]`/`[\z]` rejected by both — verified |
| Range with shorthand endpoint | `[\d-z]`, `[a-\d]` | Both engines reject (a shorthand cannot be a range endpoint) — verified |
| Bare `{` literal | `a{`, `{` | Rust rejects; Python treats as literal — divergent |
| `\Z` / braced / octal escapes | `\Z`, `\x{41}`, `\u{41}`, `\07` | Each rejected by exactly one engine — divergent (verified) |
| Verbose flag | `(?x)` | Admitted *syntax* but body semantics (whitespace/`#`) unmodeled and unverified; excluded fail-closed (§4.1) |
| Flag negation | `(?-i)a`, `(?i-s:a)` | `(?-i)` diverges (Python rejects, Rust accepts) — verified |

A pattern containing any of these stops the regex-subset parser short of end-of-input; the
validator reports the furthest-progress offset (§5.2). The lookaround/backreference rows are redundant
with what `regex-automata` rejects at compile time, but excluding them here surfaces the
failure at **generation time with a uniform message** rather than only under `cargo test`.

### 4.3 Grammar authoring notes

- **Recognizer, not a structured CST.** Labels/dispositions are chosen for parseability,
  not downstream use; the consumer reads only "parsed to end" (§5.2).
- **Recursion direction is free; encode precedence by stratification.** FLTK supports left
  recursion (`fltk-grammar-reference.md` §9.1), so the grammar is written in the natural
  textbook regex stratification — `alternation` (the `|` layer) → `concatenation` (the
  sequencing layer) → `repetition` (the quantifier layer) → `atom` (groups, classes,
  escapes, literals). `alternation` and `concatenation` may be written left-recursively
  (left-associative, the conventional reading for `|` and concatenation) or right/iterative;
  the only hard requirement is that each recursive rule carry a non-left-recursive base-case
  alternative so seed-growing has a seed (`fltk-grammar-reference.md` §9.2). Because
  alternation is PEG ordered first-match with **no** longest-match arbitration
  (`fltk-grammar-reference.md` §4.1), order each rule's alternatives most-specific-first
  (e.g. inside an `atom`, try the multi-char group/flag openers `(?:`, `(?flags:`, `(?flags)`
  before a bare `(`, and try a `char_class` or `escape` before a single literal char) so a
  shorter admitted alternative does not shadow a longer valid one and cause a spurious short
  parse. (The class negation `^` is handled as an optional prefix inside `char_class`, not as
  a separate ordered alternative, so `[` and `[^` need no relative ordering.)
- **The pattern string is the input.** The validator parses `gsm.Regex.value` — the raw
  text between the `/.../` delimiters as already stored by `fltk2gsm.visit_regex`
  (`fltk2gsm.py:168-170`). The outer `/` delimiters are not part of `value`, so the grammar
  describes regex body syntax, not the delimiters.
- **Escape `/` inside the validator grammar's own regex terminals (hard constraint).**
  `regex_subset.fltkg`'s leaf matchers are themselves `.fltkg` regex terminals, and the
  `.fltkg` `raw_string` body grammar is `value:/([^\/\n\\]|\\.)+/` (`fegen.fltkg:17`): a
  bare `/` *ends the regex terminal early*, a bare newline is forbidden, and `\\` is special.
  Therefore every `/` the validator grammar needs to recognize in the subject pattern must be
  written `\/` inside `regex_subset.fltkg` (and any backslash as `\\`). This matters because
  the portable subset admits `\/` as an escaped metacharacter (§4.1) and the in-tree corpus
  literally contains it (`([^\/\n\\]|\\.)+`, `fegen.fltkg:17`). A naive leaf class such as
  `/[\/]/` written with a bare `/` would be silently mis-tokenized by the `.fltkg` parser —
  the regex terminal would close at the first `/` — yielding a subtly wrong validator that
  still "compiles." This failure is loud only via the §7 round-trip/corpus checks, so it is
  pinned there rather than left to inspection. This is a hard authoring constraint on the
  *validator grammar's own* terminals, distinct from (and in addition to) §3 item 4's point
  that those terminals need not be cross-engine portable.
- **No whitespace skipping inside the regex grammar (resolved against the generated parser).**
  A regex pattern has no insignificant whitespace — a literal space (or tab) in the pattern
  is a character to match — so the validator must treat every input character as
  significant. `genparser generate` unconditionally injects a default `_trivia` rule
  (`[\s]+`) when none is referenced (`gsm.add_trivia_rule_to_grammar`, `gsm.py:477-504`),
  and the generated parser invokes it in exactly two places: (a) a leading
  `apply__parse__trivia` at a start rule whose first separator is WS-bearing — emitted for
  `fegen.fltkg`'s `grammar := , rule+` because of its leading `,` (`fltk_parser.py:117`);
  and (b) a `ws_after` call after every `,`/`:` separator (`fltk_parser.py:162` etc.). A
  NO_WS (`.`) separator emits neither; a `.`-quantified repetition emits no inter-iteration
  trivia (verified: the `rule+` loop at `fltk_parser.py:127-143` has no trivia call).
  Therefore the regex-subset grammar is authored with **no leading separator and only `.`
  (NO_WS) separators throughout**. The injected `_trivia` rule is then present but
  unreferenced and never invoked, so a pattern whose leading or interior character is
  literal whitespace is parsed correctly rather than silently stripped. This is a hard
  authoring constraint, not a preference: a WS-bearing separator anywhere in this grammar
  would corrupt validation of whitespace-significant patterns.

---

## 5. Proposed approach — wiring

### 5.1 Generate and commit the regex-subset parser

Add `regex_subset.fltkg` and wire its generation into `make gencode` alongside the existing
grammars (`Makefile:247-297`):

```
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/regex_subset.fltkg regex_subset fltk.fegen.regex_subset_cst \
    --output-dir fltk/fegen
```

This produces committed `fltk/fegen/regex_subset_cst.py`,
`regex_subset_cst_protocol.py`, `regex_subset_parser.py`, and
`regex_subset_trivia_parser.py` (the non-trivia `regex_subset_parser.py` is the one used;
the trivia variant is an unavoidable by-product of the `generate` command and is harmless).
The committed artifacts are normalized by `make fix` and gated by `make check`, per the
standard regen → `make fix` → commit flow (CLAUDE.md). They depend only on
`fltk.fegen.pyrt.*` + the sibling CST module (§3.1), so no Rust build is involved.

### 5.2 New module: `fltk/fegen/regex_portability.py`

A thin, dependency-light wrapper around the generated parser, so callers do not duplicate
the parse-and-check boilerplate and the logic is unit-testable in isolation:

```python
@dataclass(frozen=True)
class RegexPortabilityIssue:
    pattern: str   # the offending pattern
    offset: int    # codepoint offset of furthest progress (error_tracker.longest_parse_len)
    detail: str    # human-readable context for the message

def check_regex_portable(pattern: str) -> RegexPortabilityIssue | None:
    """Return an issue if `pattern` is outside the portable subset, else None.

    Parses `pattern` with the committed regex-subset parser. Portable iff the
    start rule both matches AND consumes the entire pattern (result is not None
    and result.pos == len(pattern)).
    """
```

Implementation parses the pattern with the generated `regex_subset_parser.Parser` over a
`TerminalSource(pattern)`, calling the start rule. **Accept/reject predicate vs. reported
offset are two distinct values and the design commits to each separately** (a start rule
returns `ApplyResult | None`, `memo.py:68-71`):

- **Predicate (accept/reject):** portable iff `result is not None and result.pos ==
  len(pattern)`. Two reject shapes both map to "non-portable": a *hard fail* where the start
  rule returns `None` (matched nothing — e.g. first char unrecognized), and a *short parse*
  where it returns an `ApplyResult` with `pos < len(pattern)` (matched a prefix, stopped
  early). `result.pos` is only meaningful in the short-parse case and is **not** the value
  reported in the error.

- **Reported offset:** always `parser.error_tracker.longest_parse_len` — the furthest
  position any terminal reached before failing. This is the same furthest-progress field
  FLTK's own `format_error_message` reports for "where did parsing fail"
  (`errors.py:25-49,126-152`; the field is `-1` until the first terminal failure). It is the
  right offset for a recognizer that deliberately *does not* match an excluded tail: for
  `[[:alpha:]]` the start rule's `result.pos` would point just past whatever prefix matched
  (an unhelpful number inside the outer `[`), whereas `longest_parse_len` points at the
  furthest the subset grammar could push before the divergent `[:` stalled it — the location
  a human wants. `error_tracker` is populated independent of labels/dispositions: the runtime
  calls `error_tracker.fail_regex`/`fail_literal` from `consume_regex`/`consume_literal` on
  *every* terminal-consume failure (`fltk_parser.py:85,95`), keyed on the current rule frame,
  so a pure recognizer's tracker is populated normally. The §6/§7 "sensible offset" tests
  pin this `longest_parse_len` choice, not `result.pos`.

A pattern that the parser *cannot start* (hard fail) and the empty-string case are handled
explicitly: empty → portable (no construct), no issue (§6); hard fail on a non-empty pattern
→ non-portable, offset = `longest_parse_len` (which is `0` if no terminal advanced).

### 5.3 Wire into the Rust generator at the user-regex term site

Place the check at the `gsm.Regex` branch of `_gen_consume_term` in
`fltk/fegen/gsm2parser_rs.py` (the author-written-regex site), **not** inside the shared
`_regex_idx` dedup table. Rationale: `_regex_idx` is also called for the generator-internal
trivia pattern `\s+` (`gsm2parser_rs.py:578`); checking there would scan an internal
pattern the author never wrote and make the validator's domain "all patterns the generator
registers" instead of "patterns the grammar author wrote." Checking at the user-term site
keeps the contract honest and the error messages truthful. (`\s+` is in the portable subset
anyway, so it would pass — but the principle stands and avoids any future internal-pattern
surprise.)

At that branch, call `check_regex_portable(term.value)`. If it returns an issue, raise
`ValueError` naming the pattern, the furthest-progress offset/detail (§5.2), and a one-line
pointer to the documented regex boundary. It propagates to the CLI as `typer.Exit(1)` via the existing
`except (ValueError, RuntimeError, NotImplementedError)` handler
(`genparser.py:386-391`) — no handler change needed. The check runs per `gsm.Regex` term
the Rust generator reaches, only when the Rust generator is invoked.

The Python generator (`gsm2parser.py`) is **not** wired to this check: the Python backend's
`re` semantics are the existing, stable baseline; the constraint exists to protect the Rust
target, and gating Python codegen would needlessly reject grammars that work fine on the
backend a consumer may still be using. (Deliberate asymmetry; §10 O1 offers a Python-side
warning if the user wants one.)

### 5.4 Documentation updates (required by the requirements)

1. **Reword the docstring** `gsm2parser_rs.py:6-15` to describe the engine difference as a
   **hard semantic boundary** (two engines that silently disagree on POSIX classes /
   `\p{}` / nested sets, not merely a compile-time lookaround restriction) and to point at
   the new generation-time validator and `regex_subset.fltkg`.
2. **Do not rewrite the regex-subset ADR.** `docs/adr/2026/06/10-rust-parser-codegen/README.md`
   is **Status: Accepted** (immutable per CLAUDE.md). The permanent-boundary prose belongs to
   the `document-scope-boundary` burndown item (ELI5 doc point 2 ties them together), which
   can now cite `regex_subset.fltkg` as the executable definition of the boundary. This
   design changes only the code docstring (item 1) and supplies the enforcement.

### 5.5 No escape hatch in the first ship (hard wall)

Ship with no opt-out. The requirement (ELI5 doc; `recommended-actions.md:112-120`) asks only
to "reject them with a clear error message"; it requests no bypass. A grammar that needs an
excluded construct still works on the Python backend (the check is Rust-only, §5.3); for the
Rust backend the author rewrites the regex into the portable subset. A whole-grammar
build-flag opt-out is rejected for the same reasons as in the prior draft — it lives in the
build invocation rather than the grammar, and it is whole-grammar rather than per-pattern, so
it would re-open the silent-divergence hole for *accidental* future constructs in the same
grammar. If a real consumer later demonstrates a need for a deliberate Rust-only construct,
add a per-pattern, in-grammar opt-out then, designed against that concrete case (§10 O3).

### 5.6 Parity corpus: add portable-but-tricky regex cases

The requirements ask to "expand the parity corpus with portable-but-tricky regex cases."
The fixture grammar `fltk/fegen/test_data/rust_parser_fixture.fltkg` already defines regex
rules and is the right home; its corpus lives in
`tests/test_rust_parser_parity_fixture.py:53+` and runs through
`tests/parser_parity.py::run_parity_corpus_entry` → `assert_cst_equal`. Add a small set of
new rules using regexes that are *portable and meant to behave identically* (ASCII
`\d`/`\w`/`\s`, alternation, anchors, quantifiers including bounded `{m,n}`, escaped
metacharacters, character ranges, non-capturing groups, ASCII `(?i)`) plus inputs
exercising boundary behavior, and assert cross-backend equality.

Constraint on added patterns: each must be **non-nullable** (cannot match the empty string)
or be placed only in rules that tolerate nullable operands. `gsm.Regex.can_be_nil` /
`_test_regex_empty` (`gsm.py:156-172`) compiles each pattern with `re.compile` and tests
`.match("")` to feed grammar validation; the fixture's quantified rules require non-nullable
operands. Choose patterns that always consume at least one character.

---

## 6. Edge cases / failure modes

- **Same-syntax / different-semantics residual (the residual ledger).** A set of constructs
  use *identical syntax* on both engines but can match differently by Unicode-DB version, so
  the subset grammar admits them (excluding them over-rejects ASCII-only grammars) and the
  divergence is documented-only — the honest limit of any static approach (§3, §10 O2). The
  ledger is:
  - `\d` / `\w` / `\s` (and `\D`/`\W`/`\S`) over non-ASCII — Unicode-class table differs by
    engine DB version.
  - `(?i)` case-folding over non-ASCII — case-fold tables differ by DB version.
  - **`\b` / `\B` over non-ASCII** — word-boundary assertions are *defined in terms of* `\w`,
    so they inherit `\w`'s exact non-ASCII divergence. The codebase already treats `\b` as a
    known static-checker blind spot (`gsm.py:439-444` names `\ba*` as a zero-width pattern the
    emptiness checker cannot see). They are admitted as ASCII-portable for the same reason as
    `\d`/`\w`/`\s` and carry the same caveat; they are listed here explicitly so the §5.4 /
    `document-scope-boundary` hand-off covers them rather than silently omitting them.

  This whole ledger — not just `\d`/`\w`/`\s` — is what §5.4 documents as a permanent boundary
  and what O2's `TODO(regex-unicode-class-divergence)` points at. §5.6 adds parity coverage
  for the *ASCII* uses of these admitted constructs.
- **Empty / trivial patterns.** An empty pattern string (`value == ""`) must be handled
  explicitly: it is nullable and is already constrained elsewhere
  (`validate_no_repeated_nil_items`, `gsm.py:433-453`); the portability check treats empty
  as portable (it contains no construct) and returns no issue, leaving emptiness handling to
  the existing path. The check must not crash on it.
- **A pattern the subset parser cannot start at all (hard fail, start rule returns `None`).**
  Reported as non-portable with offset = `error_tracker.longest_parse_len` (§5.2), which is
  `0` when no terminal advanced — so this degenerates to "offset 0" in the common case while
  still using the single committed offset source rather than a special case.
- **Recognizer completeness (under-admission = false positive).** If `regex_subset.fltkg`
  omits a genuinely portable construct, a valid grammar is rejected at Rust generation. This
  is a **loud, fixable build error**, never a silent mis-parse — the safe direction. §7 pins
  completeness by requiring every committed in-tree grammar's regexes to parse clean, and by
  unit-testing the admitted set. Widening the subset later is a localized grammar edit + regen.
- **Recognizer over-admission (false negative).** If the grammar accidentally admits a
  divergent construct (e.g. a too-loose char-class body that swallows `[:alpha:]`), a
  non-portable pattern passes. §7 pins each verified divergent construct as a
  must-be-rejected test, so over-admission of the known cases is caught. This is the
  grammar-authoring analogue of the denylist's "did we list it?" risk, but it is checked by
  positive rejection tests rather than trusted by inspection.
- **Generation error-message quality.** The error surfaces via `genparser.py:386-391` as
  `Error: <msg>` with no stack trace, so the message must be self-contained: the pattern, the
  furthest-progress offset (`error_tracker.longest_parse_len`, §5.2), a short construct hint,
  and a pointer to the documented boundary / `regex_subset.fltkg`.
- **Pattern reused across rules.** The check runs per `gsm.Regex` term (§5.3); the first
  non-portable occurrence raises. The pattern, not the rule, is the unit of portability, so
  naming the pattern suffices. The parse is cheap and pure; re-checking a repeated pattern is
  harmless (memoize on the pattern string if ever a concern).
- **The committed regex-subset parser drifting from its grammar.** It joins `make gencode`
  (§5.1), so the standard regen flow keeps it in sync; the regen-confirm step in §7 catches
  drift.

---

## 7. Test plan

After this change, the following tests exist:

**Unit tests for the portability check** (`tests/test_regex_portability.py`, new; pure
Python, no Rust build required — imports the committed `regex_subset_parser`):
- **Portable patterns return no issue:** `[a-z]+`, `[0-9]+`, `[À-ÿ]+`, `[!@#$]+`, `\d{3}`,
  `a{2,4}`, `foo|bar`, `^a.b$`, `(?i)abc`, `(?:ab)+`, `\.\*\+`, `\w+\s*\d?`, `\bword\b`
  (admitted as ASCII-portable, residual noted §6/O2), and the real in-tree patterns from
  `fegen.fltkg` (`([^\/\n\\]|\\.)+`, the literal-class pattern). The `([^\/\n\\]|\\.)+` case
  also exercises the validator grammar's own `\/`-escaping (§4.3): if a leaf rule
  mis-tokenized on `/`, this pattern would fail. Additional must-accept cases that pin the
  edge fixes (each verified portable on both engines): leading/trailing/solo literal dash
  `[-a]`, `[a-]`, `[a-z-]`, `[+\-]`, `[-]`; empty group/branch `()`, `(?:)`, `a|`, `|a`,
  `a||b`; top-level anchor/control escapes `\A`, `\z`, `\a`, `\U00000041`; bare closer
  literals `]`, `a]b`, `}`, `a}b`; non-leading literal caret `[a^b]`, `[a^]`; shorthand as a
  plain class member `[\d]`, `[\w\s]`; escape-range endpoints `[\n-\r]`, `[\x41-\x5a]`; and
  the escaped-bracket class `[\[:alpha:]]` (a class with a literal `[` followed by a trailing
  literal `]` — pins that bare `]` is a literal and the escaped `[` does not open a POSIX
  class).
- **Each excluded construct returns an issue, and the reported offset is
  `error_tracker.longest_parse_len`** (the committed offset source, §5.2 — not `result.pos`):
  `[[:alpha:]]`, `[[:^digit:]]`, `\p{L}`, `\P{N}`, `\pL`, `[a-z&&[^aeiou]]`, `[\w--_]`,
  `(?=x)`, `(?!x)`, `(?<=x)`, `(?<!x)`, `\1`, `(?P=name)`, `(?P<name>x)`. Plus the edge-fix
  rejections (each verified non-portable on at least one engine): empty class `[]`, `[^]`;
  range with shorthand endpoint `[\d-z]`, `[a-\d]`; class assertion/anchor `[\b]`, `[\B]`,
  `[\A]`, `[\z]`; bare `{` `a{`, `{`; divergent escapes `\Z`; verbose flag `(?x)a b`; flag
  negation `(?-i)a`, `(?i-s:a)`; and interior literal dash `[a-z-0]` (deliberate safe
  over-rejection, §4.2). The offset assertion checks the furthest-progress value, so the
  test pins the design's offset choice rather than recording whatever the implementation
  happened to emit.
- **False-positive guards:** the escaped, non-POSIX `[\[:alpha:]]` (escaped bracket — a
  real char class, must be **portable**) and escaped `\\p` (escaped backslash then literal
  `p` — portable). These pin that the grammar's escape handling does not mis-reject.
- **Empty pattern** returns no issue and does not crash.

**Generator integration tests** (extend `tests/` Rust-generator suite, e.g.
`test_phase4_fegen_rust_backend.py` / a focused new test):
- A grammar with a rule whose regex is `/[[:alpha:]]+/` makes
  `RustParserGenerator(...).generate()` raise `ValueError` naming the pattern and the offset.
- The same grammar generates a Python parser without error (asserts the asymmetry, §5.3).
- `genparser gen-rust-parser` on such a grammar exits non-zero with the message on stderr
  (exercises `genparser.py:386-391`).
- A grammar with only portable regexes generates Rust unchanged (no spurious rejection;
  guards under-admission end-to-end).

**Parity corpus** (`tests/test_rust_parser_parity_fixture.py`, extended per §5.6):
- New portable-regex rules + inputs assert `assert_cst_equal` across Python and Rust backends.

**Regression for the verified divergence** (the motivating bug): a test asserting the exact
`word := value:/[[:alpha:]]+/` grammar from `a2-parity.md:90-93` is now rejected at Rust
generation time.

**Whole-tree completeness check (under-admission guard at scale):** a test that runs
`check_regex_portable` over every regex in every committed in-tree grammar that the Rust
**parser** generator actually processes, and asserts all pass. This both guards completeness
and detects subset-grammar regressions; because it parses the real in-tree corpus (including
`([^\/\n\\]|\\.)+` with its `\/`/`\\` escapes) it also doubly serves as the leaf-matcher
correctness guard for the validator grammar's own `\/`-escaping constraint (§4.3): a
mis-tokenized leaf rule would make one of these portable patterns start failing.

Two facts pin the grammar list, and getting them exact matters because the check only fires
in the Rust **parser** generator (§5.3, `gsm2parser_rs.py`):

- **Parser targets vs CST-only targets.** Only three committed grammars are fed to
  `gen-rust-parser` in `make gencode` and so reach the check in production:
  `fegen.fltkg`, `rust_parser_fixture.fltkg`, and `collision_fixture.fltkg`
  (`Makefile:230-231,280,285-286`). The remaining two — `poc_grammar.fltkg` and
  `phase4_roundtrip.fltkg` — are **`gen-rust-cst`-only** (`Makefile:269-272`); their CST is
  generated for Rust but no Rust *parser* is, so the portability check never runs against
  them in production. Their regexes happen to be portable (`[_a-z][_a-z0-9]*`, `[0-9]+`,
  `"[^"]*"`), so including them in the test is harmless, but the test must label them as
  CST-only and not imply the production check covers them. The completeness test should
  therefore assert the **parser-target** set strictly, and may additionally check CST-only
  grammars as a bonus clearly marked as such.
- **Non-Rust-target grammars are excluded.** `fltk/fegen/fltk.fltkg:76` and
  `bootstrap.fltkg:21` contain a lookahead block-comment regex `/[^*]*(?:\*(?!\/)[^*]*)*/`,
  which the subset grammar correctly rejects — but neither is any kind of committed Rust
  target (`fltk.fltkg` is intentionally broken, `Makefile:249`; the committed Rust parser is
  generated from `fegen.fltkg`, whose `block_comment` uses the lookahead-free
  `(?:[^*]|\*+[^\/\*])*`, verified in `crates/fegen-rust/src/parser.rs` `REGEX_PATTERNS`).
  These are excluded.

**The parser-target list is itself a drift surface — keep it single-sourced.** Hand-copying
the three parser-target grammar paths into the test duplicates knowledge that lives
authoritatively in the `make gencode` recipe, the exact hand-maintained-per-target-list
anti-pattern the assessment is burning down elsewhere (`gencode-drift-gate`,
`remove-dead-duplicate-crate`). A future downstream-style fixture added to `gen-rust-parser`
with a non-portable regex would slip past this test until someone remembered to add it.
**Resolution:** derive the parser-target grammar list from a single source the test and the
Makefile share rather than re-listing it in the test — e.g. a small committed manifest (a
list constant or data file) of `(grammar_path → gen-rust-parser output)` that both `make
gencode` and the test read, or a glob the Makefile and test agree on. If single-sourcing is
deferred to keep this item scoped, the manual list stays but carries a
`TODO(regex-portability-target-list-drift)` (TODO.md + the comment, per CLAUDE.md) tying it
to the `gencode-drift-gate` family so it is not a silent drift hole.

**Positive-control round-trip for the committed validator parser (§6 drift):** a
test that pins the committed `regex_subset_parser.py` actually came from a clean
`regex_subset.fltkg` — e.g. regenerate the parser into a temp dir and assert it matches the
committed file, or (lighter) assert the committed parser re-parses the in-tree corpus and the
admitted/excluded unit sets identically. The §6 "drifting from its grammar" bullet names this
risk; this test discharges it as a committed gate rather than trusting the regen step.

**Existing tests that must still pass unchanged:** `all_regex_patterns_compile` emission
(`gsm2parser_rs.py:976-996`) and all current parity corpora — the check only adds rejections
for patterns already non-portable, so no currently-committed Rust-target grammar should newly
fail. (Verification step during implementation: regen all committed parsers and confirm no
in-tree Rust-target grammar trips the check; if one does, that is itself a finding.)

---

## 8. Files touched (summary)

- **New:** `fltk/fegen/regex_subset.fltkg` (portable-subset grammar).
- **New (generated, committed):** `fltk/fegen/regex_subset_cst.py`,
  `regex_subset_cst_protocol.py`, `regex_subset_parser.py`,
  `regex_subset_trivia_parser.py` — produced by `make gencode`, normalized by `make fix`.
- **New:** `fltk/fegen/regex_portability.py` (`check_regex_portable` wrapper).
- **New:** `tests/test_regex_portability.py` (check unit tests + whole-tree completeness).
- **Edit:** `Makefile` — add the `regex_subset` line to `gencode` (§5.1).
- **Edit:** `fltk/fegen/gsm2parser_rs.py` — call `check_regex_portable` at the `gsm.Regex`
  term site in `_gen_consume_term` (not inside `_regex_idx`); reword docstring (`:6-15`).
- **No edit to** `fltk/fegen/genparser.py` — existing `ValueError`→`Exit(1)` handler reused;
  no escape-hatch flag (§5.5).
- **Edit:** `tests/test_rust_parser_parity_fixture.py` + `rust_parser_fixture.fltkg` —
  portable-regex parity cases (§5.6).
- **Edit:** Rust-generator test module — generator integration + regression tests.
- **No edit to** `docs/adr/2026/06/10-rust-parser-codegen/README.md` (Accepted/immutable);
  the permanent-boundary statement is carried by `document-scope-boundary`, now able to cite
  `regex_subset.fltkg`.
- **TODO.md + `TODO(slug)`** entries only if any residual item is deferred (§10 O2).

Generated `.rs` parser files change content only if a committed in-tree Rust-target grammar
trips the check (none expected; §7). The `make fix` → commit flow (CLAUDE.md) applies to all
new and regenerated files.

---

## 9. Non-goals

- Not building a regex *equivalence prover* or differential regex fuzzer — that is the
  broader `differential-property-harness` item, which this validator complements.
- Not changing either backend's regex engine (the prior "Option B" standardization path).
  The requirement *prefers* this option where feasible — STATUS: "Do this *OR* better if
  possible: standardize python and rust on some regex library/standard that has identical
  feature set and semantics across languages" (`recommended-actions-eli5.md:122`). The
  exploration weighed it and routed to the lint: no library provides identical Python/Rust
  semantics off the shelf; PCRE2-on-both is "identical only if matching C-library versions"
  and adds an FFI dependency; the Python `regex` module is unusable from Rust
  (`exploration.md:270-301`). **Honest qualifier:** the exploration's own open-questions
  section (`exploration.md:320-328`) flags that it did **not** determine whether the PyPI
  `regex` module and `regex-automata` derive their Unicode tables from the same source/version
  — the deciding fact for the one sub-option (`regex`-PyPI-as-common-ground) that could in
  principle widen the shared subset. So standardization is **not** conclusively closed; it is
  a deliberate, acknowledged deferral. Crucially, the lint is the correct move *irrespective*
  of how that question resolves: even the larger `regex`-vs-`regex-automata` common subset "is
  still not perfectly identical" (`exploration.md:294`), so a portable-subset constraint on
  *what the grammar author may write* is still required either way — that is the realistic
  option the exploration identifies (`exploration.md:296-301`). Resolving the open Unicode-DB
  question is `differential-property-harness` / `document-scope-boundary` territory, not this
  item's.
- Not authoring the full scope-boundary documentation (that is `document-scope-boundary`);
  this item supplies enforcement, the executable subset definition, and the docstring pointer.

---

## 10. Open questions (user judgment)

- **O1 — Python-side warning.** Validate at the Rust generator only (§5.3, recommended), or
  also surface a *warning* (not a hard error) on the Python path / at grammar load so a
  Python-backend author learns their grammar is non-portable before switching backends?
  Recommended: Rust-only hard error; the Python backend is the stable baseline. User call.
- **O2 — non-ASCII `\d`/`\w`/`\s`/`\b`/`\B`/`(?i)` residual** (the full ledger, §6). Leave
  documented-only as a permanent boundary (recommended — admitting the syntax is correct for
  ASCII and excluding it over-rejects), or attempt to flag non-ASCII usage? If left, add a
  `TODO(regex-unicode-class-divergence)` per CLAUDE.md convention pointing at the documented
  limit; the TODO must name `\b`/`\B` alongside the class shorthands so the deferral is
  complete.
- **O3 — escape hatch.** Ship with no escape hatch (recommended, §5.5), or provide a
  per-pattern, in-grammar opt-out now? If the user wants a hatch, it must be designed against
  a concrete construct a real consumer needs Rust-side.
