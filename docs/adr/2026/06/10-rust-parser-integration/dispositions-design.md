# Dispositions — Phase 4 design review, round 1

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (edited in place).

design-1:
- Disposition: Fixed
- Action: §2.1 now includes the adjacent comment edit — Makefile:73-75's "positive control (fltk-cst-core present)" is generalized to "a positive control on a crate guaranteed present in that graph" as part of the same change; "No other Makefile changes" claim scoped accordingly. Verified against Makefile:73-75 (comment names fltk-cst-core verbatim; Stanzas A/B control on fltk-parser-core).
- Severity assessment: Documentation drift only — no functional breakage, but a future editor following the stale comment could wire a wrong positive control into a new stanza.

design-2:
- Disposition: Fixed
- Action: §2.2 snippet now reads `assert result.pos == len(text), parser.error_message()`; §3 "Parse failure in self-hosting test" bullet rewritten to cover both failure modes (None and partial consume), citing plumbing.py:137-144 which treats them as one failure class. Verified: plumbing.py raises with `format_error_message` on `not result or result.pos != len(...)` in both branches.
- Severity assessment: Test would still fail correctly on partial consume, but with a bare integer-comparison assertion instead of the formatted parse error — degraded debuggability in exactly the regression scenario the test exists for.
