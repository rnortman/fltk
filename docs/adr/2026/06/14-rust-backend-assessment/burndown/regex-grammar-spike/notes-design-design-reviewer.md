# Design review: regex-grammar-spike

Reviewer: design-reviewer (adversarial fact-check). Base commit a4b35b8.
Design: `docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-grammar-spike/design.md`.

Empirically validated the spike end-to-end: copied the draft grammar, parsed it
(`parse_grammar_file` → 37 rules, start rule `regex`), generated a Python parser
(`generate_parser(capture_trivia=False)` → OK), and ran every §3.3 corpus risk point and
a representative slice of §4.2 adversarial cases through `parse_text(..., "regex")`. **All
dispositions the design predicts came out exactly as predicted**, including the
empty-pattern corner (`""` → ACCEPT) and the short-parse rejections (`a**`, `a{`,
`[a-z-0]`, `[[:alpha:]]`, `\p{L}`, `(?=x)`, `\1` all → REJECT). The clockwork UUID-`\b`,
` *`, and `[0-9]('?[0-9])*` patterns all → ACCEPT. So the core feasibility thesis is
sound and the increment-1 generation path works. Findings below are about specific
load-bearing claims that are wrong or under-specified, not about the overall approach.

---

## design-1 — "`make check` enforces no-drift of committed generated artifacts" is false

Sections: §1.2 ("gated by `make check`"), §2 ("`gencode`'s own contract ... `git diff
--stat` ... Adding the regex line brings the regex artifacts under that same drift gate
automatically"), §5 Increment-1 acceptance ("`make check` passes (generated files are
clean **and gated**)"), §6 ("Handled by the standard `make gencode` → `git diff --stat`
drift gate ... the artifacts are committed and gated by `make check`"), §7 ("**Generated-
artifact gate** (Increment 1): `make check` enforces that the committed `regex_*`
artifacts match a clean regen of `regex.fltkg`").

**What's wrong.** `make check` does not regenerate code and does not diff it. `check` →
`check-ci` → `check-common`, and `check-common` runs exactly
`lint format-check typecheck test cargo-check cargo-clippy cargo-test
cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3`
(`Makefile:40,51`). `gencode` is a standalone manual target (`Makefile:247`) referenced
nowhere in the check graph (`grep -n gencode Makefile` → only the `.PHONY` line and the
target definition). The `git diff --stat` "drift gate" exists only as a comment describing
what a human sees *after manually running `make gencode`* (`Makefile:241-246`). There is no
test in the suite that regenerates a grammar and asserts the committed output matches
(grep for `diff`/`drift`/`regenerat`/`stale` in `tests/*.py` finds nothing of the sort).
CLAUDE.md's "`make check` ... enforces that committed generated code is clean" means
*clean* = passes lint/format/typecheck, **not** *up-to-date with the generator*.

**Consequence.** Increment 1's stated acceptance criterion ("`make check` passes ...
generated files are clean **and gated**") conflates two properties; only the lint/format/
typecheck one is actually enforced. An implementer who commits a hand-edited or stale
`regex_parser.py` will still pass `make check` as long as it lints — the design promises a
drift gate that does not exist, so a committed/generator mismatch can ship undetected. The
spike's claim that the artifacts "match a clean regen" is unverified by anything in CI.

**Suggested fix.** Drop the "gated by `make check` / drift gate" language. Either (a) state
plainly that `make check` only enforces lint/format/typecheck cleanliness, and the
regen-match is a manual `make gencode` + `git diff` step the implementer must run before
commit; or (b) if a real drift gate is wanted for the spike, add an explicit
regenerate-and-compare step (the lint design's "round-trip test" the design itself defers
in §6) — but that is added scope and probably not warranted for a spike.

---

## design-2 — §4.1 REJECT-case offset assertion (`longest_parse_len ≥ 0`) is not guaranteed

Section: §4.1 ("On a REJECT case, additionally assert the reported furthest-progress offset
(`parser.error_tracker.longest_parse_len`...) is a sane value (≥ 0 and ≤ `len(pattern)`),
so the suite also pins that rejections carry a usable error location"). Same idea in §3.2
and §4.2's quantifier-stacking rationale ("short parse → reject").

**What's wrong.** `ErrorTracker.longest_parse_len` defaults to `-1` and is only advanced by
a `fail_literal`/`fail_regex` call at a position (`errors.py:26,30-48`). Two REJECT shapes
common in this grammar do not guarantee `≥ 0`:
(1) A **short-parse** rejection (the design's own dominant reject mechanism, e.g. `a**`,
`a{`): the start rule *succeeds* on a prefix and `parse_text` rejects only because
`result.pos != len(terminals)` (`plumbing.py:323`). Nothing forces a terminal *failure* to
have been recorded past offset 0 — the tracker can legitimately sit at `-1` or at some
offset unrelated to where the consumable input stopped. The accept/reject boolean is
robust; the `longest_parse_len ≥ 0` lower bound is not.
(2) The `error_tracker` referenced is the one on the parser instance `parse_text` creates
internally (`plumbing.py:312,321`); `ParseResult` (the value the test sees) does not expose
it, so the suite cannot read `longest_parse_len` from the `parse_text` return value at all —
it would have to bypass `parse_text` and drive `parser.apply__parse_regex(0)` directly to
reach `parser.error_tracker` (the §3.2 lower-level path), which contradicts §4.1's "same
predicate as §3.2 (`parse_text(...).success`)".

**Consequence.** If implemented as written, the REJECT-offset assertion can spuriously fail
(tracker at `-1` on a short-parse reject) or is simply unwriteable through `parse_text`'s
return value, producing a flaky or non-compiling test — exactly in the Opus increment that
is supposed to be the rigorous one. At minimum the `≥ 0` bound is wrong for short-parse
rejects.

**Suggested fix.** Drop the `≥ 0` lower bound (allow `-1`), or assert only `≤ len(pattern)`
and "is an int", or drop the offset assertion entirely for the spike (the accept/reject
boolean is the real signal). If the offset is wanted, the test must use the §3.2 direct
`parser.apply__parse_regex(0)` path to reach `parser.error_tracker`, and the design should
say so instead of routing through `parse_text(...).success`.

---

## design-3 — §4.1 "honest-expectation cross-check" is asymmetric and gives false assurance for the dangerous direction

Section: §4.1 ("a case marked ACCEPT that Python `re` rejects, or marked REJECT that
Python `re` accepts *and* Rust accepts, is a mis-specified case and should be caught. This
keeps the Opus-authored expectations honest rather than circular").

**What's wrong (verified).** The cross-check is sound only for the ACCEPT direction
(I confirmed all §4.2 ACCEPT cases compile under Python `re`). For the REJECT direction it
is nearly useless, because the design's REJECT cases are overwhelmingly "Python accepts,
Rust rejects/diverges" — exactly the cases the Python-only cross-check **cannot** catch.
Verified with `re.compile`: `[a-z-0]` (OK on Python — rejected only for FutureWarning/`--`
risk), `a{` (OK on Python — Rust errors), `{` (OK on Python), `\07` (OK on Python — Rust
rejects octal). The cross-check's REJECT clause requires "Python accepts *and* Rust
accepts" to flag a mis-spec, but the suite has no inline Rust oracle (O3 is deferred), so
the Rust half is never evaluated. The over-admission direction (a REJECT case that is
actually portable, i.e. both engines accept it) — the one §4 calls "the dangerous
direction" — is therefore unguarded by the cross-check.

**Consequence.** The §4.1 cross-check, as scoped, validates almost nothing about the
hand-authored REJECT expectations (which are the bulk of the adversarial suite and the
whole point of "fool the parser"). An Opus-authored REJECT case whose rationale about Rust
divergence is simply *wrong* (the construct is in fact portable) sails through: Python
accepts it, the grammar rejects it, the test passes, and a real over-rejection finding is
masked as "expected." The design presents this cross-check as keeping expectations "honest
rather than circular," but for REJECT cases it remains effectively circular.

**Suggested fix.** State explicitly that the Python `re` cross-check only validates the
ACCEPT direction and that REJECT-case correctness rests entirely on the rationale string +
human/Opus judgement (no oracle). If REJECT correctness matters for the spike's value,
elevate O3(b) (the tiny `cargo` Rust-acceptance helper) from optional to required for the
adversarial increment — it is the only thing that makes the REJECT cross-check real.

---

## design-4 — Increment 3 "snapshot helper" partly reinvents existing enumeration; O4 leaves it under-specified

Sections: §3.4 ("a small committed helper (script or a `make` target, recorded as O4)"),
§5 Increment 3, §8, O4.

**What's wrong / scope note.** The snapshot helper's core (parse `clockwork.fltkg`, walk
the GSM, collect distinct `gsm.Regex.value`) is the *identical* enumeration the corpus test
already implements per §3.1. The design treats the helper as a separate artifact whose form
is an open question, but it is the same `collect_regexes(grammar)` function pointed at a
different path plus a JSON-with-provenance writer. Verified: clockwork at HEAD
`ea343880` yields the distinct bodies the design expects (` *`, `[^\n]*`,
`[_a-zA-Z][_a-zA-Z0-9]*`, `[0-9]('?[0-9])*`, `[eE]`, the UUID `\b` pattern, and the
string-literal pattern) — 7 distinct, not the exploration's stale "~6 distinct" (§7
`:362`), and clockwork's grammar is unchanged from what the exploration sampled.

**Consequence.** Minor. Risk is duplicated walk logic drifting between the helper and the
test (two copies of the same enumeration), and an implementer burning effort designing a
"helper" that should just import the corpus test's collector. Left as O4 + "script or make
target," it is the kind of open question that becomes a coin-flip during implementation.

**Suggested fix.** Specify that the helper imports the same `collect_regexes` used by the
corpus test (single source of truth for the walk), and that its only added responsibility
is reading the out-of-tree path + emitting the JSON provenance header. Then O4 is purely
"where does the one-line entry point live (script vs make target)," which is genuinely a
trivial preference.

---

## design-5 — Increment independence claim is slightly overstated (Inc 3 ⊄ independent of Inc 2)

Section: §5 ("Each independently committable"); Inc 3 ("Independent of Increment 2 in
principle, but ordered after it so the corpus-test module exists"); Inc 4 ("Independent of
Increments 2–3 in content").

**What's wrong.** Inc 3 *extends* `tests/test_regex_grammar_corpus.py`, the module created
by Inc 2 (§5 Inc3 bullet 2: "Extend `test_regex_grammar_corpus.py`"). It is therefore not
independently committable from Inc 2 — it edits Inc 2's file and reuses Inc 2's collector
(§3.1). The "independent in principle" hedge concedes this but the §5 header flatly claims
each increment is independently committable.

**Consequence.** Low. The stated *ordering* is fine and each increment leaves the tree
green; the only inaccuracy is the "independently committable" framing for Inc 3, which an
orchestrator might read as "can be reordered/parallelized." It cannot be — Inc 3 has a hard
file/function dependency on Inc 2.

**Suggested fix.** Reword: Inc 1 is the foundation; Inc 2 and Inc 4 each depend only on
Inc 1; Inc 3 depends on Inc 1 **and Inc 2** (shares the corpus module + collector). Drop
"Independent of Increment 2 in principle" for Inc 3.

---

## Verified-correct (no action needed)

- Grammar generates cleanly through the Python pipeline; start rule `regex`; 37 rules.
  `parse_text(..., "regex").success` is the right oracle (`plumbing.py:323`).
- `_for_each_item(items, visitor)` signature and `rule.alternatives` iteration match the
  §3.1 collector exactly (`gsm.py:291-302,40`). Rust codegen uses the same `term.value`
  field.
- fegen.fltkg has exactly the 6 distinct regex bodies §3.3 lists (note line 21
  `block_comment` carries two: content + end). The §3.1 "programmatic, not hand-list"
  insistence is well-justified — `grep` extraction produces false positives on lines like
  `. "` (verified), which the GSM walk avoids.
- Every §4.2 ACCEPT case compiles under Python `re` (verified). Every §3.3 corpus risk
  point and the empty-pattern corner behave exactly as the design predicts (verified by
  running the generated parser).
- Regex.fltkg line citations spot-checked (`:316-322`, `:172-184`, `:80-83`) are accurate.
- `gsm.Regex.value` holds the decoded body (outer `/.../` stripped) — §3.1/§3.3's
  "collected strings are post-decode" is correct (`fltk2gsm.visit_regex`).
- Clockwork is out-of-tree (`/home/rnortman/tps/clockwork/...`, confirmed present) and CI
  cannot reach it; the snapshot-with-provenance approach is sound, and the chosen JSON
  format correctly preserves whitespace-significant patterns (` *`).
</content>
</invoke>
