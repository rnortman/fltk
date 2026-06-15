# Dispositions — docs/fltk-grammar-reference.md review (round 1)

Source: notes-grammardoc-review.md. Each finding fact-checked against the actual code
(memo.py, gsm2tree.py, terminalsrc.py/.rs, the grammar files, and the cited test) before
disposition. Findings design-1..design-3 are citation/grounding defects (claims true,
pointers wrong/missing); design-4 is the reviewer's own confirmed non-finding; design-5 is a
low-value optional clarification.

design-1:
- Disposition: Fixed
- Action: §9.1 ("Associativity") and the §13 quick-ref row. Re-grounded the
  left-associativity claim on `_grow_seed` (`memo.py:228-257`, esp. the store at
  `251-252`), where each growth cycle re-runs the head rule and wraps the just-stored shorter
  result as the left child. Recast the `test_regression_recursive_inlining.py:35-178` citation
  to pin its actual content (recursive result is nested, not spuriously inlined) and noted
  the test parses a single-`+` input so it cannot by itself distinguish left from right
  associativity. The §13 row code column changed from the test to `memo.py:228-257 (esp.
  251-252)`.
- Severity assessment: Verified against source — the cited test asserts only `has_nested_expr`
  (lines 162-176) on input `"x+ "` (single `+`, one possible nesting shape) and its docstring
  states its purpose is the bug-#1 spurious-inlining regression, not associativity. Miscited
  grounding on the document's single most load-bearing behavioral claim directly undermines
  the doc's stated credibility contract ("any claim can be checked against the code"); a
  maintainer verifying associativity against that test would find it unpinned and might weaken
  a true claim.

design-2:
- Disposition: Fixed
- Action: §3.2. Changed the citation from `gsm2tree.py:425`-region to
  `class_name_for_rule_node`, `gsm2tree.py:46-47`.
- Severity assessment: Verified — `gsm2tree.py:423-426` is the `for c in sorted(allowed_classes)`
  dedup loop inside `_emit_py_mutators` (unrelated to naming); `class_name_for_rule_node` at
  `46-47` is the actual no-suffix camel-case function. The claim (no `Node` suffix) is the
  public-API-stability point the drop-in-replacement contract rests on; pointing a verifier
  at unrelated mutator code erodes trust exactly where the doc most needs it. The correct
  citation was already used in §3.1.

design-3:
- Disposition: Fixed
- Action: §8.4 sentence and the §13 "Negative position" row. Added the Python-side grounding
  for `pos == len` acceptance: `consume_literal` fails only when `pos + literal_len >
  terminals_len`, and `consume_regex` uses `re.match(..., pos=pos)`, both succeeding at
  `pos == len` (`terminalsrc.py:168-181`). The §13 row code column now lists both
  `terminalsrc.rs:33-37, 139` and `terminalsrc.py:168-181`.
- Severity assessment: Verified by inspection of `terminalsrc.py:168-181`. The claim ("both
  backends accept") is correct; only the Rust side was cited. Low impact (claim true) but a
  cross-backend behavioral-equivalence assertion is precisely what a downstream consumer
  relies on for drop-in safety, and the doc promises a citation per claim — the gap was
  inconsistent with its own standard.

design-4:
- Disposition: Won't-Do
- Action: None. The reviewer recorded this as an explicit non-finding / confirmation, not a
  defect.
- Severity assessment: None. The §6.3 claims are accurate as written.
- Rationale (Won't-Do): Verified that `bootstrap.fltkg:13` defines `inline:"!"` in the
  `disposition` rule and that no item in any live grammar (`fegen.fltkg`, `bootstrap.fltkg`,
  `toy.fltkg`, `unparsefmt.fltkg`, `rust_parser_fixture.fltkg`) applies `!` — the only `!`
  disposition uses are `fltk.fltkg:11` and `:34` (the `rust_parser_fixture.fltkg:36` hit is a
  `"!"` string literal, not a disposition). §6.3 already states the live grammars "define the
  glyph but never apply it to an item," which covers both `fegen.fltkg` and `bootstrap.fltkg`.
  The reviewer themself records "No defect in the claim ... none" as the consequence. Adding
  a bootstrap.fltkg name-drop would lengthen an already-correct passage with no accuracy gain;
  there is nothing to fix.

design-5:
- Disposition: Fixed
- Action: §2.1. Added one clause noting that the lowercase-snake_case rule constrains
  rule/label names *in `.fltkg` itself*, and that a consumer grammar may define its own
  `identifier` rule with any regex (citing `unparsefmt.fltkg:87`'s uppercase-allowing
  `/[a-zA-Z_][a-zA-Z0-9_]*/`).
- Severity assessment: Verified — `unparsefmt.fltkg:87` does define the looser regex (the
  exploration's mention of `fltk.fltkg:87` was off; `fltk.fltkg:62` is lowercase-only, so the
  doc cites only the confirmed `unparsefmt.fltkg:87`). Very low impact; the §2.1 claim about
  the `.fltkg` meta-grammar was already correct. Applied as a pure clarity improvement that
  preempts confusion for a reader looking at a consumer grammar with uppercase identifiers.
