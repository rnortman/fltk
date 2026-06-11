# Judge verdict — design review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: design. Doc: `docs/adr/2026/06/10-rust-parser-integration/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings.

## Findings walk

### design-1 — Fixed
Claim: §2.1's "No other Makefile changes" foreclosed updating the recipe comment (Makefile:73-75), which says "positive control (fltk-cst-core present)" — inaccurate once Stanzas A/B control on `fltk-parser-core`. Consequence: stale maintainer comment could steer a future editor to wire the wrong positive control.
Source check: Makefile:74 reads "Uses a positive control (fltk-cst-core present) before the negative assertion" verbatim; design §2.1 Stanzas A/B do `grep -q fltk-parser-core`. Finding accurate.
Fix check: design.md §2.1 now reads "One adjacent comment edit: the recipe's explanatory comment (Makefile:73-75) ... Generalize it to 'a positive control on a crate guaranteed present in that graph'", and the "No other Makefile changes" claim is scoped to exclude that edit (success message at Makefile:87 remains accurate as claimed).
Assessment: fix addresses the comment exactly as suggested. Accept.

### design-2 — Fixed
Claim: §2.2 snippet's bare `assert result.pos == len(text)` gives no diagnostic on partial consume, while §3 claimed error-message coverage of parse failure; Python reference treats None and partial consume as one failure class. Consequence: regression on fegen.fltkg stopping short fails with `assert 1234 == 5678` and no error context — degraded debuggability in exactly the scenario the test exists for.
Source check: plumbing.py:137 (`if not result or result.pos != len(terminals.terminals)`) raises with `format_error_message` for both modes — finding's premise confirmed.
Fix check: design.md §2.2 snippet now reads `assert result.pos == len(text), parser.error_message()` with a "partial consume is a failure too" comment; §3 "Parse failure in self-hosting test" bullet rewritten to cover both failure modes, citing plumbing.py:137-144 and noting the tracker holds the farthest failure.
Assessment: fix matches the suggested remedy in both the snippet and the edge-case section. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable.
