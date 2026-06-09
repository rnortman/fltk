# Dispositions: design review rework round — rust-cst-child-span-test

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Verdict: `judge-verdict-design.md` (REWORK). Prior dispositions: `dispositions-design.md`. Disputed: design-1 only; design-2 and design-3 approved, not re-examined.

design-1:
- Disposition: Fixed (completed)
- Action: Judge's residual claim verified against `TODO.md` at HEAD af6e6f3: lines 44-46 are inside the `## gencode-poc-fltkg` entry; the `## rust-cst-child-node-identity` entry spans lines 40-42. Corrected the last stale citation at design.md:66 from `TODO.md:44-46` to `TODO.md:40-42`, matching the already-corrected citation at design.md:13 for the same entry. Grepped design.md for all `TODO.md:` citations post-edit — three remain (design.md:13 `40-42`, :37 `35-37`, :66 `40-42`), all verified correct and mutually consistent.
- Severity assessment: The stale citation pointed at a different live TODO entry (`gencode-poc-fltkg`) and contradicted design.md:13, undermining the doc's exact-HEAD-citation authority; one-line fix.
