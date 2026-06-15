# Design review — fltk-grammar-reference.md + regex.fltkg

Adversarial fact-check at base commit a4b35b8. The reference doc is overwhelmingly
accurate: I verified the load-bearing claims (left-recursion seed-grow, PEG first-match,
disposition semantics + INLINE NotImplementedError in both backends, separator/trivia
semantics, the `re` vs `regex-automata` boundary, CST spans/suppression-gaps/labeled-access/
cross-backend identity) directly against source and they hold. Findings below are the
exceptions: one substantive grammar bug, a few groundedness/terminology nicks, and minor
citation drift.

---

## design-1 — regex.fltkg: `U` flag is NOT in the Python∩Rust portable subset (false positive)

Section: regex.fltkg `flag_chars := value:/[imsxU]+/ ;` (line 119), used by `flag_group`
(`(?flags:...)`, line 111) and `inline_flags` (`(?flags)`, line 117).

What's wrong: the allowlist admits the `U` inline flag. Python `re` rejects `(?U)` and
`(?U:...)`:

```
>>> re.compile("(?U)a")    -> re.error: unknown extension ?U at position 1
>>> re.compile("(?U:a+)")  -> re.error: unknown extension ?U at position 1
```

(verified by running CPython at this commit). `U` (swap-greediness) is a Rust-`regex`-only
inline flag; it is not in the common subset. The portable flag set is `[imsx]` (all four
verified to compile on Python `re`: `(?i) (?m) (?s) (?x) (?ms) (?i:abc)` all OK).

Why this matters: the file's stated contract (lines 8-13) is that a pattern is "portable
(behaves identically on Python `re` and Rust `regex-automata`) iff this grammar parses it to
end of input," and that non-portable constructs are "ABSENT and therefore rejected by
construction." Including `U` violates that invariant in the *wrong* direction: the lint
would accept `(?U:a+)` / `(?U)` as portable when they fail to even compile on the Python
backend.

Consequence: a downstream grammar author relying on this lint to keep their grammar
cross-backend-portable could ship a regex using `(?U...)`, pass the portability check, and
then have the Python backend break at runtime (`re.error`) — the exact cross-backend
divergence the lint exists to prevent. This is a correctness bug in the allowlist, not just
an unproven first cut.

Suggested fix: `flag_chars := value:/[imsx]+/ ;` and drop the `U` mention. (Also reconsider
whether `x` verbose-mode scoping is truly behavior-identical across engines before relying
on it, but `x` at least compiles on both; `U` does not.)

---

## design-2 — Reference overstates what the recursive-inlining test pins (left-associativity)

Section: §9.1 "Associativity"; §13 table row "Associativity of direct left recursion" —
both cite `test_regression_recursive_inlining.py:35-178` as pinning **left-associative**
nesting, e.g. "For `expr := expr "+" | "x"` on input `x+`, the result is
`expr(left=expr("x"), "+")` ... pinned by `test_regression_recursive_inlining.py:35-178`."

What's wrong: that test (`fltk/fegen/test_regression_recursive_inlining.py:139-176`) parses
input `"x+ "` (a single growth level) and asserts only that a *nested* `Expr` node exists in
the children (`has_nested_expr`) — i.e. that the recursive result is not spuriously
flattened/inlined. For a single-level input, left- vs right-associative nesting are
indistinguishable; the test never parses a two-level input (e.g. `x++`) and never asserts
which side the nested node sits on. The test's docstring asserts the expected shape but the
assertions do not enforce associativity direction.

Why this matters: the left-associativity claim is still *true* (it follows from `_grow_seed`
re-running the head rule and wrapping the prior result as the new outer node,
`memo.py:228-257`, which I verified), but the cited test is not the evidence for it. A reader
who opens that test to "check the claim against the code" (the doc's stated promise, line 5-6)
will find it does not pin associativity.

Consequence: a load-bearing groundedness claim points at a citation that does not support it;
on the reference's own "any claim can be checked against the code" standard, this is a
verification gap. Low blast radius (the underlying behavior is correct) but it undercuts the
doc's central trust contract.

Suggested fix: cite `memo.py:228-257` (`_grow_seed`) as the mechanism for associativity, and
either downgrade the test citation to "pins non-flattening of recursive results" or point at
a test that actually exercises multi-level associativity if one exists.

---

## design-3 — Regex-subset terminology: doc says "regex-syntax"/"regex-automata"; the cited ADR says "the Rust `regex` crate"

Section: §8.3 and §13 table ("Grammar regexes must use the common subset of Python `re` and
**`regex-syntax`**"; "Python `re` and `regex-syntax`"), citing
`docs/adr/2026/06/10-rust-parser-codegen/README.md`.

What's wrong: the cited ADR (README.md:50-51) states the subset as "the common subset of
Python `re` and the Rust **`regex` crate**" and refers to "the Rust `regex` crate" / the
`fancy_regex` alternative — it does not say `regex-syntax` or `regex-automata`. The runtime
actually uses `regex_automata::meta::Regex` (terminalsrc.rs:8), and `gsm2parser_rs.py:6-15`
hedges by naming "`regex` and `regex-automata` crates (shared `regex-syntax`)". So three
different crate names are in play across doc/ADR/code for one boundary.

Why this matters: these crates share the `regex-syntax` frontend so the *substance* of the
subset claim is consistent, but a "canonical reference … grounded in source; citations given
so any claim can be checked" (lines 3-6) should name the same artifact the ADR it cites
names. A reader cross-checking §8.3 against the ADR will find a different crate name.

Consequence: reader confusion / apparent contradiction between the reference and its cited
authority; no behavioral error. Minor.

Suggested fix: align terminology — state the engine is `regex_automata::meta::Regex` whose
syntax frontend is `regex-syntax` (shared with the `regex` crate), and note the ADR phrases
it as "the Rust `regex` crate."

---

## design-4 — Minor citation drift (non-blocking)

The reference's `file:line` citations are mostly exact, but a few are off by a line or two.
Flagging because the doc explicitly markets line-accurate citations as its trust mechanism
(line 5: "citations are given as `file:line` so that any claim can be checked").

- §9.5 / §13 cite the Rust corner-case `panic!` at `memo.rs:225-228`; the actual
  `panic!("Untested corner case…")` is at `memo.rs:227` (within that range — fine).
- §6.2 / §7.4 cite label defaulting at `fltk2gsm.py:113-116`; the assignment is at
  `fltk2gsm.py:113-114`.
- §8.3 / §8 enforcement cites the Rust compile test at `parser.rs:1346-1347`; the test
  `fn all_regex_patterns_compile` opens at `parser.rs:1344`, panic at `1347`.

Consequence: trivial; each lands on or adjacent to the cited construct. No claim is wrong.
Worth a pass only because the doc's value proposition is citation precision.

---

## Verified accurate (high-confidence, checked against source)

- Self-describing grammar reproduced verbatim from `fegen.fltkg:1-22` (exact).
- bootstrap.fltkg / fltk.fltkg characterizations: bootstrap lacks `ws_required:":"`, plain
  `_trivia`, literal `block_comment` end; fltk.fltkg header "actually broken and was never
  completed" (`fltk.fltkg:2`) with `!alternatives` at `:11`,`:34`. All confirmed.
- Disposition defaulting (`fltk2gsm.py:117-122`), `%`-on-subexpression assert
  (`gsm2tree.py:629`), INLINE NotImplementedError Python (`gsm2parser.py:782-784`) + Rust
  (`gsm2parser_rs.py:824-826,1010-1012`), Invocation rejection (`gsm2parser_rs.py:768-770`).
- PEG first-match (`gsm2parser.py:718-732`), suppress gate (`:802`), separator NO_WS/WS_REQ
  handling (`:642-643,684,696-697`), greedy progress + `+` guards (`:570-577,595-599`).
- Left-recursion seed-grow mechanism (`memo.py:82-156,206-257`), base-case-required
  (`memo.py:104-106,147-149`), per-position recursion key (`memo.py:80`).
- Rust depth guard `DEFAULT_MAX_DEPTH=1000` + sticky flag (`memo.rs:74,190-201`), Python no
  guard, Python bindings `RecursionError` (`parser.rs` pyo3 section).
- Regex matching: Python `re.compile(regex).match(self.terminals, pos=pos)`
  (`terminalsrc.py:178`); Rust anchored full-haystack search (`terminalsrc.rs:141-166`),
  `pos<0` reject, `pos==len` accept; word-boundary context tests (`terminalsrc.rs:368-389`).
- CST: span sentinel `-1`/overwrite, `_span_start` captured pre-mutation
  (`gsm2parser.py:535-536,743-763`), Span eq ignores `_source`/`kind` (`terminalsrc.py:54-55`),
  UnknownSpan `Span(-1,-1)` (`:152`), cross-backend canonical-name eq/hash
  (`gsm2tree.py:99-156`), empty-model rejection (`:251-256`), mutator strictness order
  child→label→index (`:531-603`).
- All `rust_parser_fixture.fltkg` line citations (arrow/latin_word/tagged/val/grouped/
  rec_via_sub/nest_sum/expr/lval/rval/paren_expr/stmt) match.

## regex.fltkg additional notes (not faulted — first cut, conservative-reject acceptable)

- Empty group `()` and empty alternation branches are rejected (no nil base case in
  `alternation`/`concatenation`/`capturing.body`). Both are valid+portable in `re` and Rust,
  so these are false negatives. Conservative for an allowlist; acceptable but worth knowing.
- `\b`/`\B` (`assertion`, line 186) are accepted inside character classes via the shared
  `escape`/`class_atom` path, where `\b` semantically means backspace, not word boundary.
  Doesn't admit a non-portable construct, so harmless for the allowlist; semantically imprecise.
- All separators are `.` (NO_WS) and there is no leading separator anywhere (verified by
  scan), so the whitespace-significance claim in the header holds and the auto-injected
  `_trivia` is never reachable. `.fltkg` self-escaping of `/` and `\` in the terminals
  (`meta_escape`, `class_char`, `literal_char`) is valid per `raw_string`'s grammar. No
  `%`-suppressed sub-expressions (all `%` are on literals/regex), so no `gsm2tree.py:629`
  violation.
