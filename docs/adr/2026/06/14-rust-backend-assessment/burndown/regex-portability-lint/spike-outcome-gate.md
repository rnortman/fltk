# Spike-outcome gate: `regex-grammar-spike` → `regex-portability-lint`

**Decision date:** 2026-06-14
**Decision type:** Pre-authorized conditional gate (user delegated; see "Authority" below)
**Verdict: CLEAN-POSITIVE — `regex-portability-lint` may proceed autonomously.**

---

## Authority for this decision

The user pre-approved the `regex-portability-lint` implementation conditionally, gated
on the just-completed `regex-grammar-spike`. Verbatim criteria:

> "If the regex spike proves we can parse regexes and distinguish in-scope vs
> out-of-scope regex features, then we can proceed with the regex-portability-lint
> implementation; my approval not needed. If the spike result is more complicated then
> that's something I'll weigh in on."

So this gate evaluates two criteria — (a) can the grammar parse regexes, and (b) can it
distinguish in-scope vs out-of-scope features *cleanly enough for the portability lint's
purpose* — and renders CLEAN-POSITIVE (proceed without the user) or COMPLICATED (escalate).

The spike is squashed at commit `862b412`. This assessment is grounded in its actual
artifacts: `fltk/fegen/regex.fltkg`, `fltk/fegen/regex_corpus.py`,
`tests/test_regex_grammar_adversarial.py` (~151 cases, all passing),
`tests/test_regex_grammar_corpus.py`, the spike implementation log, and the lint's own
`design.md`.

---

## Criterion (a): Can the grammar parse regexes? — YES, conclusively.

- **Real-corpus coverage is proven, not asserted.** `test_regex_grammar_corpus.py` runs
  the generated parser over every distinct regex in the in-tree grammars (`fegen.fltkg`
  and `regex.fltkg` itself) and asserts every one is accepted. This includes the
  non-trivial production patterns the lint must handle on day one: the `.fltkg`
  raw-string body `([^\/\n\\]|\\.)+`, the block-comment content `(?:[^*]|\*+[^\/\*])*`,
  the literal-value alternation `("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')`, the identifier
  class `[_a-z][_a-z0-9]*`, etc. These exercise capturing/non-capturing groups,
  alternation, negated classes, the `\/`-self-escaping hazard the design called out
  (§4.3), and `+`/`*` quantifiers.

- **The grammar is self-describing.** `regex.fltkg`'s own 12 leaf-regex terminals are all
  accepted by the parser generated from it (`test_regex_fltkg_self_referential`).

- **Structural breadth is exercised** by the adversarial suite: deep nesting (5-level
  groups, 26-way alternation), left-recursive alternation/concatenation, lazy
  quantifiers, anchors, the dot metacharacter, empty/nilable shapes, and a required
  UTF-8/non-ASCII battery (2/3/4-byte codepoints, astral plane, RTL/bidi, NFC vs NFD) —
  the codepoint-vs-byte hazard class that is the one thing the in-tree ASCII corpus could
  not probe.

The only observed parsing limit is a parser-*implementation* stack-overflow at ~50 levels
of nesting (`RecursionError` at the default recursionlimit), explicitly noted as a
recursive-descent depth limit, **not** a grammar semantic gap, and well outside any real
pattern. It does not bear on the lint.

**Criterion (a) is met without qualification.**

---

## Criterion (b): Can it distinguish in-scope vs out-of-scope cleanly enough for the lint's purpose? — YES.

The lint's purpose, per `design.md` §2, is an **allowlist that fails CLOSED**: a pattern
is portable iff the grammar parses it to end of input; anything unrecognized is rejected
by construction. The design's entire safety argument rests on the *over-rejection*
direction being the safe one (§6: "a loud, fixable build error, never a silent
mis-parse") and the *over-admission* direction (false negatives) being the one to watch.

The spike's headline result is exactly the shape the lint wants:

- **ZERO over-rejections of any portable construct.** Every genuinely-portable shape
  probed — including the tricky ones the design enumerates as must-accept (leading/
  trailing/solo dashes `[-a]`/`[a-]`/`[a-z-]`/`[+\-]`/`[-]`, empty groups/branches,
  `\A`/`\a`/`\U…` escapes, bare closers `]`/`}`, non-leading caret `[a^b]`, shorthand
  class members `[\d]`/`[\w\s]`, escape-range endpoints `[\n-\r]`/`[\x41-\x5a]`, the
  escaped-bracket near-miss `[\[:alpha:]]`) — is accepted. This is the criterion that, if
  failed, would have made the lint reject working grammars and forced annotation/grammar
  churn on out-of-tree consumers. It is clean.

- **The headline divergent classes the lint exists to catch all fail closed correctly.**
  POSIX classes `[[:alpha:]]`/`[[:^digit:]]` (the literal motivating bug from the
  assessment, `a2-parity.md`), Unicode properties `\p{…}`/`\P{…}`/`\pL`, lookaround
  `(?=`/`(?!`/`(?<=`/`(?<!`, backreferences `\1`, named groups `(?P<…>`/`(?P=…)`, the
  `--` set-difference look-alike (interior dash excluded), `\Z`, braced `\x{..}`/`\u{..}`,
  bare `{` (`a{`), open-min/empty/unterminated bounds, the verbose flag `(?x)`, flag
  negation `(?-i)`/`(?i-s:)`, and the in-class assertion/anchor divergences
  `[\b]`/`[\A]`/`[\z]` — **all rejected.** Every divergent construct the design's §4.2
  table and §7 must-reject test list names is correctly rejected by the grammar.

So the grammar draws the in-scope/out-of-scope line cleanly on every construct the lint's
design actually enumerates as a target. That is the "distinguish in-scope vs out-of-scope"
the user's criterion (b) asks for.

---

## The over-admissions: do they undermine the lint? — No. Tolerable and handled-by-design.

The spike honestly documents six over-admissions (grammar accepts a construct at least one
engine rejects). I assess each FROM THE LINT'S PERSPECTIVE — i.e., does it cause the lint
to wave through a genuinely-non-portable pattern in a way that re-opens the silent-
divergence hole the lint exists to close?

| ID | Construct | Why admitted | Real-world harm to the lint |
|----|-----------|--------------|------------------------------|
| F1 | `\0N` octal (`\07`, `\00`, `\012`) | `\0` is a valid `control_escape` (null), trailing digit is a literal | Low. Pattern still **compiles** on Rust? No — Rust *rejects* octal, so the existing `all_regex_patterns_compile` cargo-test gate (design §5, `gsm2parser_rs.py:976-996`) catches it as a hard Rust compile error. The lint missing it ≠ silent divergence. |
| F2 | `U` inline flag (`(?U)`, `(?iU)`, `(?U:a)`) | `flag_chars /[imsU]+/` admits `U` by **deliberate design** (§4.1 lists `U` as admitted) | None. `U` is Rust-valid; it is non-portable only *toward Python*, and the lint is **Rust-only by design** (§5.3). This is intended behavior, not a gap. |
| F3 | `\z` top-level anchor | `anchor_escape /[Az]/` admits `z`; Rust accepts, Python rejects | None for the lint's stated purpose. `\z` is Rust-valid; Python-only non-portability is out of the Rust-only lint's scope (same logic as F2). The only artifact is a stale "verified on both engines" comment in `regex.fltkg:276-280` — a doc nit, not a lint defect. |
| F4 | inverted bound `a{2,1}` (min>max) | `bounded` is purely syntactic; no min≤max predicate | Low. **Both** engines reject it → Rust rejects at compile → caught by `all_regex_patterns_compile`. A context-free grammar *cannot* express min≤max; this is intrinsic to the recognizer approach, exactly as the design anticipated (§6: "a grammar validates syntactic membership… it cannot detect" semantic predicates). |
| F5 | reversed class range `[z-a]` (lo>hi) | `class_range` is purely syntactic; no lo≤hi predicate | Low. Same as F4: **both** engines reject → Rust compile-time catch. Intrinsic semantic predicate, not a grammar-expressible constraint. |
| F6 | `&&` set-intersection look-alike (`[a-z&&b]`, `[a&&b]`) | `&` is an ordinary `class_char` (not excluded) | Low-to-moderate, but still caught downstream. Rust treats `&&` as real set-intersection; Python warns (`FutureWarning`). The two engines *do* diverge here, so this is the one over-admission in the genuinely-silent class. BUT: the design already lists `&&` set-ops as an excluded construct (§4.1, §4.2 table, §7 must-reject list: `[a-z&&[^aeiou]]`). The spike's own existing `&&` case rejects (for an unrelated inner-`[` reason); F6 is the *bracket-free* `&&` form that slips through. |

**Why none of these blocks the lint from proceeding:**

1. **Five of six (F1–F5) are not in the silent-divergence class the lint exists to close.**
   F2/F3 are Rust-valid constructs non-portable only toward Python — explicitly out of
   scope for the Rust-only lint by design. F1/F4/F5 are rejected by **Rust at compile
   time**, so they are already caught by the pre-existing, untouched
   `all_regex_patterns_compile` cargo-test gate (design §5). The lint's job is to catch
   constructs that *compile cleanly on both engines but match differently* — F1/F4/F5
   don't compile cleanly on Rust at all, so the existing gate, not the lint, owns them.
   The lint passing them through is a no-op, not a hole.

2. **F4/F5 are intrinsic to the chosen approach and were anticipated by the design.**
   `min≤max` and `lo≤hi` are semantic predicates a context-free grammar provably cannot
   express. The design already states this limit explicitly (§3 "the one honest limit",
   §6) and routes such residuals to documentation / a downstream semantic check. The spike
   confirming this predicted limit is *consistent with* the design, not a surprise that
   contradicts it.

3. **F6 is the only genuinely-silent over-admission, and it is already a named target of
   the design.** The design's §4.1/§4.2/§7 all list `&&` set-operations as excluded and as
   a must-reject test. The spike merely discovered that the *current grammar text* closes
   the `--` door (interior dash excluded from `class_char`) but leaves the `&&` door open
   (`&` is an ordinary `class_char`). This is a **localized grammar edit** — exclude `&`
   from `class_char` (or require an explicit escaped `\&`, mirroring how `-` is already
   handled) — squarely within the lint implementation's scope, and the design's §7 already
   demands a `[a-z&&…]`-style must-reject test that will *fail until that edit is made*,
   forcing the fix during implementation rather than letting it ship. The remediation is
   a few characters in one terminal, with an existing test slot waiting for it.

In short: the over-admissions are either (a) out of the lint's Rust-only scope, (b) caught
by the pre-existing Rust-compile gate, (c) provably impossible for a grammar and already
documented as a downstream-semantic-check residual, or (d) F6 — a one-line grammar
tightening the design already calls for. **None re-opens the silent-divergence hole; none
requires a design change; none requires a user judgment call.** The findings are exactly
the kind of "feed the go/no-go" outputs the spike was built to produce, and they land on
the tolerable side of the line the design already drew.

---

## Decision-relevant cross-check against the design

The design's §7 test plan already enumerates the must-accept and must-reject sets the
spike validated, and §6 already commits to over-admission being checked by "positive
rejection tests" rather than trusted. The spike's findings are therefore **inputs the
design was built to receive**, not contradictions of it. The single actionable item the
spike surfaces beyond what the design text already covers is the F6 `&&` grammar
tightening — and even that has a test slot waiting in §7. There is no open design question,
no scope expansion, and no irreversible/hard-to-reverse choice that would warrant pulling
the user in under their own stated rule ("if the spike result is more complicated").

---

## Verdict

**CLEAN-POSITIVE.** Both of the user's criteria are met: (a) the grammar parses regexes
(proven against the full in-tree corpus plus a broad adversarial + UTF-8 battery, all
green), and (b) it distinguishes in-scope from out-of-scope features cleanly enough for
the lint's fail-closed allowlist purpose (zero over-rejections of portable constructs;
every divergent construct the design targets is correctly rejected). The documented
over-admissions do not materially undermine the lint: they are out-of-scope, already
caught by the existing Rust-compile gate, intrinsic-and-documented, or a one-line grammar
tightening the design's own test plan already forces.

Per the user's pre-authorization, **`regex-portability-lint` may proceed autonomously; the
user's approval is not required.**

### Carry-forward notes for the implementation (not blockers)

1. **Tighten F6 during implementation.** Exclude `&` from `class_char` (mirror the `-`
   treatment) so `[a-z&&b]`/`[a&&b]` reject; the design's §7 already specifies the
   matching must-reject test. This is the one grammar edit the spike strictly motivates.
2. **F1/F4/F5 belong to a downstream semantic check, not the grammar.** They cannot be
   expressed context-free. Document them as the residual the design's §6/§10-O2 ledger
   already anticipates (a `TODO(slug)` if deferred, per CLAUDE.md), and lean on the
   existing `all_regex_patterns_compile` Rust gate to catch them in the meantime.
3. **Fix the stale comment** at `regex.fltkg:276-280` ("portable… verified on both
   engines") — `\z` is Rust-only, not Python-portable (F3). Cosmetic, but it currently
   misstates a verified fact.
