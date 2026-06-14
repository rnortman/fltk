# A2 — Cross-Backend Equivalence Risk (adversarial assessment)

Dimension question: *How confident can we be that the Rust backend produces
behaviorally-equivalent parse results and CST shapes to the Python backend across the full
grammar feature space?*

One-line verdict: **ADEQUATE for the narrow grammar family FLTK self-hosts on, but WEAK as a
general drop-in guarantee.** The equivalence that *is* tested is tested well (a real
recursive structural comparator, error-equivalence, a full self-host GSM-equality check that
actually runs in the gate). But the test method is **63 hand-picked corpus inputs over two
fixture grammars with zero property/differential/fuzz testing**, and the two backends run
**two genuinely different regex engines** (`re` vs `regex-automata`) whose semantic
divergences are essentially untested. The "full grammar feature space" claim in the dimension
question is *not* substantiated by the test suite — large regions of it (every regex feature
not literally present in two fixture grammars, INLINE/Invocation, separator-bearing
repetition, deep-nesting span arithmetic on arbitrary grammars) are unverified, and several
have concrete silent-divergence paths.

The single most dangerous finding: a grammar regex using a POSIX class like `[[:alpha:]]`
**compiles on both engines and parses completely differently** — `regex-automata` treats it
as an ASCII alpha class; Python `re` treats it as the nested character set `[:alph]`. Same
input, different parse tree, no error, no test. (a2-parity:posix-class-divergence)

---

## How equivalence is actually established (the method, scrutinized)

There are exactly three mechanisms, and it is worth being precise about what each does and
does not cover.

### 1. Parser-level structural parity corpus (`tests/parser_parity.py` + two corpora)

- `assert_cst_equal` (`tests/parser_parity.py:10-42`) is a *real* recursive comparator: it
  checks `kind`, `span.start`/`span.end`, child count, per-child label equality, node-vs-span
  species (via `hasattr(child, "children")`), and recurses. It is not a no-op — the fegen
  suite contains thorough comparator self-tests proving it fails on kind/span/child-count/
  label/species/deep-nesting mismatches (`test_rust_parser_parity_fegen.py:104-339`). Good.
- The corpus is **hand-picked**: 19 entries for fegen (`test_rust_parser_parity_fegen.py:46-85`,
  measured: 19 outcome tuples) and 44 for the fixture (`test_rust_parser_parity_fixture.py:53-128`,
  measured: 44 tuples). 63 inputs total, each run with `capture_trivia ∈ {False, True}`.
- That is the **entire** parse-equivalence verification surface. There is **no property-based
  testing, no fuzzing, no differential testing** anywhere in the suite: `grep -rn hypothesis
  tests/` → 0 hits; `hypothesis` is not a dependency in `pyproject.toml`; no random/generative
  grammar or input generation in the parity files.

### 2. Self-host GSM equality (`test_clean_protocol_consumer_api.py:353-361`)

`python_gsm == rust_gsm` after running BOTH backends through the **same** `Cst2Gsm` pipeline.
This is the strongest single check, but its coverage is narrower than it looks:
- It runs only on **one grammar** (`fegen.fltkg`).
- `Cst2Gsm.visit_items` (`fltk/fegen/fltk2gsm.py:50-106`) **discards trivia and collapses
  structure** via positional interleaving with hard `assert`s. So this test compares the
  *post-filter semantic model*, not the raw CST. Trivia placement, span-of-suppressed-element,
  and child-ordering differences that `Cst2Gsm` normalizes away are invisible to it.
- `_span_text` (used by `visit_literal`/`visit_regex`/`visit_identifier`) reads source text by
  span offsets. If spans diverged, the GSM would silently contain different literal/regex
  strings — a wrong value, not a crash — *unless* the divergence also broke the positional
  `assert`s.

### 3. CST-node construction/mutation parity (`test_cst_mutators_parity.py`,
`test_cross_backend_label_equality.py`)

These cover the *constructed* CST surface (insert/remove/replace/clear, label/NodeKind
eq/hash) well and are not the concern of this dimension (they don't exercise the parser). They
are solid.

**Bottom line on method:** equivalence is asserted by example, not by construction or by
property. The comparator is good; the corpus is small and grammar-specific; the regex engine
boundary is essentially untested. Confidence outside the two fixture grammars is low.

---

## FINDINGS

### a2-parity:posix-class-divergence — POSIX classes / regex-engine divergence parse silently differently — **BLOCKER**

**Location:** `crates/fltk-parser-core/src/terminalsrc.rs:141-166` (Rust uses
`regex_automata::meta::Regex`) vs `fltk/fegen/pyrt/terminalsrc.py:177-181` (Python uses
`re.compile(regex).match`). Compile-gate: `fltk/fegen/gsm2parser_rs.py:976-996`.

**Observation:** The two backends run **two different regex engines**. The generated
`all_regex_patterns_compile` test (`gsm2parser_rs.py:980-996`) only proves a pattern
*compiles* under `regex-automata`; it proves nothing about *matching equivalence* with Python
`re`. I verified a concrete, fully-silent divergence directly by compiling a probe against the
workspace's `regex-automata` build and the system `re`:

- Pattern `[[:alpha:]]` (verified by direct execution): **Rust `regex-automata` matches any
  letter** (`a,l,p,h,z,e` → MATCH; `:,[,]` → NO — the standard POSIX alpha class). **Python
  `re` matches NOTHING** — across all ASCII printable chars `re.match(r"[[:alpha:]]", c)` is
  empty (it parses `[[:alpha:]]` as a malformed nested set + trailing literal, emitting a
  `FutureWarning`). So a rule `word := value:/[[:alpha:]]+/` **parses `"hello"` on Rust and
  fails to parse it entirely on Python** — same grammar, same input, opposite outcome, no
  generation-time error on either side.
- POSIX classes (`[[:digit:]]`, `[[:space:]]`, `[[:alnum:]]`, …) all compile cleanly on the
  Rust side and all mean something entirely different to Python `re`. The compile gate passes;
  the parse silently diverges.

More broadly, `re` and the `regex` crate differ on `(?i)` case-folding tables, named Unicode
property classes (`\p{...}`), the exact `\d`/`\w`/`\s` Unicode tables (tied to each engine's
Unicode DB version), and POSIX/nested-set syntax. None of these is differentially tested.
(I *did* verify the one pattern shared by **both** backends — the hardcoded trivia `\s+` —
agrees across the engines for 10 representative whitespace codepoints incl. U+2028/U+00A0/
U+1680/U+3000, so the trivia path itself is safe; the danger is entirely in
**user-grammar regexes**.)

**Why it matters:** FLTK's whole reason for existing is that out-of-tree consumers write their
own `.fltkg` grammars. The grammar regex surface is *the* primary place a consumer's grammar
meets the engine boundary, and it is the least-defended. A consumer whose Python-backed
grammar uses any POSIX class, Unicode property class, or relies on `re`'s specific
`\d`/`\w`/`\b` Unicode behavior will get a **different parse tree** on the Rust backend with no
error and no test catching it — a direct violation of the near-drop-in contract.

**Remediation:** (a) Document the regex engine as a *hard semantic boundary*, not "the common
subset" — the current docstring (`gsm2parser_rs.py:6-15`) understates it as merely a
compile-time restriction. (b) Reject POSIX-class / nested-set / `\p{}` syntax at generation
time with an explicit error, or differentially test it. (c) Add a differential regex harness:
for every grammar pattern, generate inputs and assert `re.match` and `regex-automata` agree on
match length across a corpus, run in the gate.

**Severity:** blocker. **Confidence:** high (verified by direct execution against the
workspace's own `regex-automata` build and system `re`).

---

### a2-parity:no-property-testing — Equivalence is asserted by 63 hand-picked examples, not by property/differential/fuzz testing — **MAJOR**

**Location:** `tests/test_rust_parser_parity_fegen.py:46-85` (19 entries),
`tests/test_rust_parser_parity_fixture.py:53-128` (44 entries); absence of any generative
harness across `tests/`.

**Observation:** The cross-backend parse-equivalence guarantee rests entirely on 63
hand-authored `(rule, text, expected)` tuples over two fixture grammars. There is no
property-based testing (no `hypothesis`), no grammar fuzzer, and no differential testing that
feeds randomized or corpus-mined inputs through both backends and compares. For a system whose
correctness claim is "behaviorally equivalent across the full grammar feature space," example
coverage of ~63 inputs is far short of the claim. The corpus author has to *think of* each
divergence to test it — exactly the inputs an adversary or an unusual real grammar will find
are the ones not in the list.

**Why it matters:** Every divergence below (`posix-class-divergence`, `sep-in-repetition`,
`error-token-order`) is the kind of thing a property/differential harness would surface
automatically but a hand-picked corpus structurally cannot. The maintenance model (two
string-emitting generators kept in lockstep "by convention + tests" — see u3/u4 notes) means
the test corpus is the *only* backstop against drift, and it is sized for confidence in the
fixtures, not in arbitrary consumer grammars.

**Remediation:** Add a differential test: generate a corpus of grammars (or mine real ones
incl. Clockwork's), and for each, generate random conforming + malformed inputs, parse with
both backends, and run `assert_cst_equal`/`assert_error_equiv`. Gate it.

**Severity:** major. **Confidence:** high.

---

### a2-parity:fixture-feature-gaps — Whole grammar features are unverified or NotImplementedError on Rust, so "full feature space" parity is false — **MAJOR**

**Location:** INLINE disposition `gsm2parser_rs.py:824-826,1010-1012`; Invocation terms
`gsm2parser_rs.py:768-770`; separator-bearing repetition (no fixture coverage, see below);
deep-nesting span arithmetic (only `nest`/`nest_sum` to depth 2 in the fixture,
`test_rust_parser_parity_fixture.py:99-108`).

**Observation:** Several grammar features are either explicitly unsupported on Rust or simply
absent from both fixture grammars:
- **INLINE disposition (`!term`)** and **Invocation terms** raise `NotImplementedError` in the
  Rust parser generator. A grammar using either parses on Python and *fails to generate* on
  Rust. This is why FLTK self-hosts on the reduced `fegen.fltkg` and marks the richer
  `fltk.fltkg` (which uses `!alternatives`, lines 11/34, and lookahead regex `(?!\/)`, line 76)
  "intentionally broken." So the in-tree self-host evidence is over the *easier* grammar.
- **Separator-bearing repetition.** Neither fixture has a repeated item with a whitespace
  separator *between repetitions* at the `+`/`*` level (e.g. `item:atom , item:atom`); the
  fixture's `+`/`*` rules (`items := item:atom+`, `zero_items := item:atom*`,
  `rust_parser_fixture.fltkg:22,28`) are all NO_WS. The repeated-separator path exists only
  inside sub-expressions in fegen (`alternatives := items , ( "|" , items , )*`). The
  Python `gen_item_parser_multiple` (`gsm2parser.py:505-618`) and Rust `_gen_item_multiple`
  (`gsm2parser_rs.py:667-730`) emit *structurally different* loop+separator code; the
  cross-backend equivalence of the loop's trivia/separator placement at the repetition level
  is thinly covered.

**Why it matters:** The dimension question is about the *full* feature space. For INLINE/
Invocation the honest answer is "not equivalent — Rust refuses." For separator-bearing
repetition the answer is "unverified." A consumer with an inline-disposition grammar cannot
migrate at all; a consumer with separated repetition is trusting an untested codegen path.

**Remediation:** Either implement INLINE/Invocation on Rust or document them as a hard
non-parity list visible to consumers (they are not in `TODO.md`). Add fixture rules with
WS_ALLOWED/WS_REQUIRED separators between `+`/`*` repetitions and add them to the parity
corpus.

**Severity:** major. **Confidence:** high.

---

### a2-parity:error-token-order-masked — The parity comparator is deliberately loosened to *hide* a real backend divergence in error-token ordering — **MAJOR**

**Location:** `tests/parser_parity.py:112-116` (`_assert_messages_equiv` compares token sets
**unordered**); Rust error builder `crates/fltk-parser-core/src/errors.rs:123-184` vs Python
`fltk/fegen/pyrt/errors.py:126-149`.

**Observation:** The comparator compares the per-rule expected-token lines as **sets**
(`assert py_rules[rule_name] == rust_rules[rule_name]`), with an explicit comment that this is
"unordered — Python iterates a set, Rust first-occurrence" (`parser_parity.py:112`). That is
the comparator being **engineered around a known divergence**: the two backends emit the
"Expected: …" tokens in **different orders** in the actual error string a human/consumer reads.
The error-format strings themselves are independently hand-re-implemented in two languages
(byte-pinned format literals duplicated at `errors.rs:149,184` and `errors.py:140,149`), held
equal only by these 63 corpus inputs.

**Why it matters:** The formatted error message *is* part of the public surface — consumers
display it, snapshot-test it, or scrape it. The backends produce **observably different
message text** (token order differs), and the parity suite is specifically written not to
catch that. A consumer who asserts on exact error text (a common pattern) will see their tests
break when switching backends, and the in-tree parity suite gives false assurance that error
output is equivalent. Separately, the duplicated byte-pinned format strings are a silent-drift
surface: a one-sided edit to a format literal not covered by a corpus input passes CI.

**Remediation:** Either make the two backends emit tokens in the same order (then tighten the
comparator to ordered compare) or explicitly document that error-message token order is
backend-dependent and unstable, so consumers do not assert on it.

**Severity:** major. **Confidence:** high.

---

### a2-parity:trivia-only-2-examples — Raw-CST trivia/whitespace equivalence rests on 2 comment inputs and is normalized away by the only self-host check — **MAJOR**

**Location:** trivia corpus inputs `test_rust_parser_parity_fegen.py:62-64` (one line-comment,
one block-comment); production trivia gate `fltk/plumbing.py:166` (`capture_trivia=False`);
self-host filter `fltk/fegen/fltk2gsm.py:50-106`. Historical root-cause:
`docs/adr/2026/06/05-cst-type-annotations-regression/trivia-divergence-rootcause-v2.md`.

**Observation:** A **real production trivia divergence already happened**: the Rust path
defaulted to `capture_trivia=True` while the committed Python parser used `capture_trivia=False`,
so the two backends produced structurally different CSTs (Rust had `(None, Trivia)` children
Python lacked). It was patched by forcing `capture_trivia=False` at `plumbing.py:166` and by
masking it with the `Cst2Gsm` trivia filter. Consequences for *parity confidence*:
- The **production** self-host path now never exercises trivia capture at all
  (`capture_trivia=False`), so the strongest test (`python_gsm == rust_gsm`) tells us nothing
  about trivia-capture equivalence.
- Raw-CST trivia equivalence (where trivia *is* captured) is checked only by the parity
  corpus, and only by **2 comment examples** in the fegen corpus (a line comment and a block
  comment), parametrized over `capture_trivia`. The fixture grammar has **no comment/trivia
  rule at all** (`grep _trivia/line_comment/block_comment rust_parser_fixture.fltkg` → none),
  so the 44-entry fixture corpus contributes zero trivia-capture coverage.
- The fegen `_trivia` rule is non-trivial: `( line_comment | line_comment? : | block_comment )+`
  — it contains a WS_REQUIRED separator *inside a trivia rule* and a `+` over an alternation of
  comment forms. The interaction of comment-capture with the inner separator at the repetition
  boundary is exercised by exactly the two corpus inputs above.

**Why it matters:** That a divergence in this exact area already shipped and required a filter
+ a forced flag to paper over is direct evidence the surface is fragile, and the regression
test for it (2 comment inputs) is thin. A consumer who *does* want trivia capture (e.g. for a
formatter front-end) is relying on a path that diverged once and is barely tested.

**Remediation:** Add comment/trivia rules to the fixture grammar and several trivia-capture
parity inputs covering comment-then-whitespace, interleaved comments, and trivia at
start/end-of-input; add a raw-CST (pre-`Cst2Gsm`) trivia-structure equality assertion to the
self-host test under `capture_trivia=True`.

**Severity:** major. **Confidence:** high.

---

### a2-parity:weak-species-discriminator — `assert_cst_equal` distinguishes node-vs-span children by `hasattr(child,"children")`, which can mask type-level divergence — **MINOR**

**Location:** `tests/parser_parity.py:29-42`.

**Observation:** The comparator's only check that a child is "the same kind of thing" across
backends is structural duck-typing: `py_is_node = hasattr(py_child, "children")`. For node
children it then recurses (checking `kind`), but for **span** children it compares only
`start`/`end` — never the source text, never any type identity. Two spans with equal offsets
but (hypothetically) different captured content, or a child that is a span on one backend and a
differently-typed leaf on the other but still answers `hasattr(...,"children")` the same way,
would pass. It also never asserts the cross-backend `kind`/label equality goes through the
canonical-name path (it relies on `==` working, which is fine, but it doesn't *prove* the
canonical mechanism is what's matching).

**Why it matters:** The comparator is the oracle for the entire corpus. A weak oracle weakens
every one of the 63 inputs simultaneously. The span-child check in particular ignores content,
so a span-offset-correct-but-content-wrong divergence (e.g. from the regex-engine differences
above producing the same length but a different intended capture) would slip through.

**Remediation:** For span children, also compare `_span_text`/source slice, not just offsets.
Assert child label equality goes through the canonical-name identity explicitly.

**Severity:** minor. **Confidence:** medium.

---

### a2-parity:gate-skips-on-bare-pytest — The entire parity surface silently skips outside `make`, so "green" can mean "ran nothing" — **MINOR (process)**

**Location:** `tests/test_rust_parser_parity_fegen.py:13-16`,
`tests/test_rust_parser_parity_fixture.py:13-16` (`pytest.importorskip`); guarded only by the
`Makefile` `test: build-test-fixtures` dependency.

**Observation:** Every parity test is gated by `pytest.importorskip("fegen_rust_cst" /
"rust_parser_fixture")`. A bare `uv run pytest` on a checkout that hasn't run
`make build-test-fixtures` skips the *entire* cross-backend surface and reports green. The only
defense is the Makefile dependency plus a docstring warning ("A CI lane where every test here
is skipped is a failure signal"). The obvious first command an out-of-tree consumer or new
contributor runs (`pytest`) gives a misleadingly clean result with zero equivalence checks
executed.

**Why it matters:** It is not a correctness bug, but it directly undermines *confidence in the
equivalence guarantee*: the guarantee only holds if the tests actually ran, and the harness
makes "didn't run" look identical to "passed." Combined with the small corpus, the effective
coverage in a casual run is zero.

**Remediation:** Make the skip loud (a sentinel test that *fails* if the fixtures are absent in
a CI context, or a session-scoped check), or build the fixtures from a `conftest` fixture so
plain `pytest` exercises them.

**Severity:** minor (process). **Confidence:** high.

---

## Risk rating: downstream consumer switching backends gets different results

**Medium-to-high**, concentrated in two areas:

1. **Grammar regexes (high).** Any consumer grammar using a POSIX class, a Unicode property
   class, or relying on Python `re`'s specific `\d`/`\w`/`\b` Unicode behavior can silently
   parse differently on Rust. This is the most likely real-world divergence because regexes are
   ubiquitous in grammars and the engine boundary is the least-tested surface.
   (`a2-parity:posix-class-divergence`)

2. **Unsupported features (deterministic).** INLINE disposition and Invocation terms don't fail
   *subtly* — they fail to generate. A consumer using them can't migrate at all, and nothing in
   `TODO.md` flags this. (`a2-parity:fixture-feature-gaps`)

For the **narrow family of grammars resembling the two fixtures + fegen** (literal/regex over
ASCII-ish classes, the standard quantifiers/separators/dispositions, left recursion, multibyte
literals), confidence is genuinely **high** — those paths are well-comparated and run in the
gate. The problem is precisely that the dimension question asks about the *full* feature space,
and the test method (63 examples, two grammars, one regex pattern shared, no property testing,
two different regex engines) does not support a full-space equivalence claim.
