# Deep correctness review — regex portability classification

Reviewed commit: `ba953c8` (range `034252d..ba953c8`).
Focus: does `check_regex_portable` (`fltk/fegen/regex_portability.py`) plus the subset
grammar (`fltk/fegen/regex.fltkg`) correctly distinguish portable vs non-portable per the
design's Python-`re` / Rust-`regex-automata` scope boundary? Hunt for false negatives
(genuinely non-portable patterns that pass) and false positives.

Method: ran `check_regex_portable` over the full design admit/reject corpus (§4.1/§4.2),
then cross-checked suspect constructs against **both** real engines — Python `re` (with
`FutureWarning`→error) and `regex-automata` 0.4.14 built with the *exact production feature
set* from `crates/fltk-parser-core/Cargo.toml` (`default-features=false`, `std syntax perf
unicode meta nfa-backtrack nfa-pikevm hybrid dfa-onepass`). The entire design corpus
classifies exactly as the design specifies — no deviation there. The findings below are
constructs **outside** that corpus, or corpus items whose admit-decision the design asserts
was "verified on both engines" but empirically is not.

The wrapper-level mechanics are correct: empty→portable short-circuit (line 83),
predicate `result is not None and result.pos == len(pattern)` (line 90), offset sourced from
`error_tracker.longest_parse_len` (line 95), `max(offset,0)` only in the message while the
stored `offset` retains `-1`/raw — all match design §5.2. No off-by-one, leak, or control-flow
defect in the wrapper. Every finding is a grammar admit-set error surfacing through it as a
false negative.

---

## correctness-1 — `\0` (and every bare-`\0` form) is admitted but Rust rejects it

**File:** `fltk/fegen/regex.fltkg:299` — `control_escape := value:/[nrtfv0a]/`

**What's wrong.** The `0` in the `control_escape` class admits `\0` as a portable NUL escape.
It is not portable: `regex-automata` (production feature set) **rejects** every bare-`\0`
form, while Python `re` accepts `\0` as NUL. Verified directly:

| pattern | `check_regex_portable` | Python `re` | `regex-automata` 0.4.14 (prod features) |
|---------|------------------------|-------------|------------------------------------------|
| `\0`    | PORTABLE               | OK (matches NUL) | **ERR (parse error)** |
| `\0a`   | PORTABLE               | OK          | **ERR** |
| `[\0]`  | PORTABLE               | OK          | **ERR** |

**Why.** `escape_body`/`class_escape_body` → `char_escape` → `control_escape` (`regex.fltkg:292-299`)
matches `\0`. Rust regex-automata has no `\0` escape at all — a NUL must be written `\x00`
(or a class) — so it fails to compile. This contradicts design §4.1's claim that `\0` was
"verified portable on both engines," and contradicts the in-repo adversarial test's own
assertion that "`\0` (null)... BOTH engines accept `\0`"
(`tests/test_regex_grammar_adversarial.py:319`, the `\0a` case). The adversarial suite frames
the `\0` problem narrowly as octal-*ambiguity* of `\0`+digit (F1); the real defect is broader:
**`\0` itself is non-portable**, independent of any following digit.

**Consequence.** A grammar author writes `rule := x:/\0/` (or `/\0+/`, `/[\0]/`) — a perfectly
ordinary way to match NUL on the Python backend. It passes the portability lint, then **fails
Rust parser generation** at the `all_regex_patterns_compile` gate (`gsm2parser_rs.py:976-996`)
or at runtime `Regex::new`. The lint's whole contract is to catch exactly this — a pattern
that works on Python but breaks on Rust — at generation time with a clear, located message.
It instead lets it through to a downstream Rust compile failure with no portability context.
This is a false negative against the lint's core invariant ("admitted ⇒ behaves identically on
both engines").

**Suggested fix.** Drop `0` from `control_escape`: `value:/[nrtfva]/`. This also collapses the
entire F1 `\0N` octal family (`\00`, `\07`, `\012`, `[\07]`) — all of which Rust likewise
rejects — into a single correct rejection, since none start with an admitted escape anymore.

---

## correctness-2 — `(?U)` / `(?iU)` / `(?U:…)` admitted but Python rejects the `U` flag

**File:** `fltk/fegen/regex.fltkg:159` — `flag_chars := value:/[imsU]+/`

**What's wrong.** `U` is admitted as an inline/scoped flag char. Python `re` has **no `U`
flag** and rejects it (`unknown extension ?U`); `regex-automata` accepts it. Verified:

| pattern  | `check_regex_portable` | Python `re` | `regex-automata` |
|----------|------------------------|-------------|------------------|
| `(?U)a`  | PORTABLE               | **ERR (`unknown extension ?U`)** | OK |
| `(?iU)a` | PORTABLE               | **ERR** | OK |
| `(?U:a)` | PORTABLE               | **ERR** | OK |

**Why.** `inline_flags`/`flag_group` (`regex.fltkg:142,148`) draw flags from `flag_chars`,
which includes `U`. Design §4.1 explicitly lists `(?U)` among admitted flags "(portable as
syntax)" — but it is not portable: it is Rust-only, and a Python-backend grammar using it does
not compile. This is the inverse-direction sibling of the (correctly rejected) `\z` decision:
`\z` is Rust-valid/Python-invalid and the grammar *deliberately admits* it (design §4.1, with a
"Rust-only check, F3" rationale), so by that same stated rationale `(?U)` admission is at least
internally consistent — **but** the module's own docstring and the design frame the subset as
"behaves identically on Python `re` and Rust `regex-automata`" (`regex_portability.py:3-5`),
which `(?U)` violates.

**Consequence.** A grammar with `(?U)` (a deliberate Rust-only choice or a copy-paste from Rust
docs) passes the lint and generates a Rust parser fine, but the *same grammar on the Python
backend* fails to compile — breaking the near-drop-in cross-backend contract in the
Python-rejects/Rust-accepts direction. Less dangerous than correctness-1 (it is a loud Python
compile error, not a silent mis-parse), but it is a portability false negative the lint claims
to cover. Note: the adversarial suite already records this as finding F2
(`tests/test_regex_grammar_adversarial.py:509-524`) and *chose not to fix it*, deferring to the
design's admit-list. Flagged here so the disposition is a conscious one: the docstring's
"behaves identically on both engines" claim and the admission of `U` cannot both stand.
Either drop `U` from `flag_chars`, or amend the docstring/design to state the subset is
"Rust-valid and not-silently-divergent" rather than "identical on both engines."

---

## correctness-3 — reversed bounded quantifier `{m,n}` with m>n admitted (`a{3,1}`)

**File:** `fltk/fegen/regex.fltkg:92-95` — `bounded`

**What's wrong.** `bounded` is purely syntactic: `"{" min:number "," max:number "}"` with no
`min ≤ max` check. `a{3,1}` is admitted. **Both** engines reject it (Python: "min repeat
greater than max repeat"; `regex-automata`: parse error). Verified PORTABLE via the checker.

**Consequence.** A reversed-bound pattern passes the lint, then fails Rust generation at
`all_regex_patterns_compile`. A CFG cannot express the `min ≤ max` predicate, so this is the
documented class of "rejected by both engines at compile time" that the design (§4.2 closing
note) says is "redundant with what `regex-automata` rejects at compile time." Lower stakes than
correctness-1/-2 because it is non-portable on *both* engines (no silent divergence) and is
caught downstream — but it is still an admitted non-portable pattern, i.e. a false negative
relative to the stated "the parser stalls short on non-portable constructs" promise. Already
recorded as adversarial finding F4. Acceptable to leave **if** the design explicitly accepts
"both-engines-reject ⇒ caught later by the compile gate" as out of scope; flagged so that
exclusion is deliberate, not assumed.

---

## correctness-4 — reversed character range `[z-a]` (lo>hi) admitted

**File:** `fltk/fegen/regex.fltkg:201` — `class_range := lo:class_range_atom "-" hi:class_range_atom`

**What's wrong.** `class_range` is syntactic only; `[z-a]` (lo>hi) is admitted. Both engines
reject it (Python: "bad character range z-a"; `regex-automata`: rejects out-of-order range).
Verified PORTABLE via the checker. Same class as correctness-3 (a `lo ≤ hi` semantic predicate
a CFG cannot express), already recorded as adversarial finding F5
(`tests/test_regex_grammar_adversarial.py:186`).

**Consequence.** Identical shape to correctness-3: passes the lint, fails the Rust compile
gate; non-portable on both engines, no silent divergence. Same disposition question — if the
design accepts the compile gate as the backstop for both-reject cases, this is out of scope;
flagged for an explicit decision rather than a silent gap.

---

## Not findings (verified correct)

- Entire design §4.1 admit corpus and §4.2 reject corpus classify exactly as specified — POSIX
  classes, `\p{}`, set ops `&&`/`--`, lookaround, backrefs/named groups, empty classes,
  class-context `\b`/`\A`/`\z`, shorthand range endpoints, bare `{`, `\Z`, `(?x)`, flag
  negation, interior class dash — all correctly rejected; all listed must-accepts portable.
- The in-tree corpus pattern `([^\/\n\\]|\\.)+` (`fegen.fltkg:17`) — correctly **portable**
  (an early shell-escaping artifact suggested otherwise; re-tested with a clean Python literal,
  it passes). The validator-grammar `\/`/`\\` self-escaping (§4.3) is intact.
- `\a` (bell): admitted, and both engines accept it — correct (it is `0a` minus the `0`).
- `\Z`, `(?-i)`, `(?i-s:)`, `\07`-as-octal, `\g<1>`, `(?#…)` comment group, `(?>…)` atomic,
  `\Q…\E`, possessive `a++`, nested `a**`, `\K`, `(?<name>x)` — all correctly rejected.
- Offset reporting uses `error_tracker.longest_parse_len` per §5.2; sampled offsets
  (`[[:alpha:]]`→1, `[a-z&&…]`→4, `{`→0) point at the stall location as designed.

The wrapper logic is correct; all four findings are admit-set errors in `regex.fltkg`.
correctness-1 is the consequential one (silent Python/Rust divergence the lint exists to catch);
correctness-2 is a real but louder portability gap; correctness-3/-4 are both-engines-reject
cases backstopped by the compile gate and may be intentionally out of scope.
