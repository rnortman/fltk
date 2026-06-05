# Judge verdict — requirements review

Phase: requirements. Doc: `requirements.md` (cross-backend label equality). Round 1.
Notes: 1 reviewer file; 7 findings. All dispositioned Fixed.
Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

No code phase → no Added-TODOs walk. Each Fixed claim verified against the requirements doc text.

## Other findings walk

### requirements-1 — Fixed
Claim: §Performance "(Pin: precompute/intern...)" prescribes mechanism; consequence is designer boxed out of a cheaper zero-alloc static-string scheme against the request's "mechanism is design's call." Real consequence.
Doc §114: bullet retitled "Performance (non-blocking SHOULD; mechanism is design's call)"; Pin deleted; technique explicitly left to design, naming precompute/intern/`&'static str` match/integer-keying as options. §113 Co-generation retains "equality computed from the canonical name each side already knows" — constrains the key (no shared registry), not a caching technique; correctly not treated as a mechanism pin.
Assessment: fix addresses the consequence. Accept.

### requirements-2 — Fixed
Claim: "must not regress meaningfully" is unenforceable and undefined, sitting among gated ACs; consequence is a slow design passing review while appearing constrained. Real. Reviewer offered two options (coarse perf AC OR downgrade to non-blocking SHOULD).
Doc §114: "There is no measured perf acceptance criterion; 'no meaningful same-backend regression' is a design goal, not a gated AC." Responder took the downgrade option, avoiding a fabricated "X% of baseline" threshold not grounded in request/exploration. Internally consistent with requirements-1.
Assessment: reviewer-sanctioned option, applied cleanly. Accept.

### requirements-3 — Fixed
Claim: §104 rationale named only the Rust side; consequence is a Rust-only fix silently failing AC1's `py == rust` direction because Python's `enum.Enum.__eq__` short-circuits before the reflected richcmp. Verified against exploration framing; real and load-bearing.
Doc §110: "Both generators must emit custom equality"; Python `enum.Enum` identity `__eq__` must be overridden; Python side must yield `NotImplemented` (not `False`) for foreign operands so reflected Rust richcmp runs; "a Rust-only fix is insufficient."
Assessment: addresses the exact short-circuit the finding named. Accept.

### requirements-4 — Fixed
Claim: §56 equates `False` and `NotImplemented` ("equivalently"); they coincide only for not-equal cases. Consequence: a uniform-`NotImplemented` design breaks AC1 when both sides defer. Low risk (AC1 forces equal case True) but genuine.
Doc §61: caveat added — `NotImplemented` acceptable "only where the correct answer is `False`"; equal case "MUST return `True` as a value from at least one side, else both-`NotImplemented` falls back to identity and yields a wrong `False`."
Assessment: matches the prescribed constraint. Accept.

### requirements-5 — Fixed
Claim: no in-tree consumer exercises cross-backend path (exploration §146/§178/§201-202/§218); doc presents AC9 as a real consumer, risking the work being scoped as fixing a live bug. Reviewer explicitly framed this as premise-statement, not veto. Verified against cited exploration sections.
Doc §15: "Premise" paragraph added, citing the exploration sections; states all in-tree consumers are same-backend by construction, this future-proofs the drop-in contract, AC9 is a constructed demonstration not a regression guard.
Assessment: states the premise the finding asked for. Accept.

### requirements-6 — Fixed
Claim: §38 asserted cross-grammar non-equality "because `<ClassName>` differ," contradicting OQ4's concession that ClassName can collide; consequence is a silent soundness hole if a design leans on ClassName-as-grammar-disambiguator. Real, low-likelihood.
Doc §40-43: rewritten — canonical name is "rule+label scoped" and "does not encode grammar identity"; three cases enumerated (same-grammar diff, distinct-rule legitimate collision, cross-grammar collision); cross-grammar collision acknowledged possible and deferred to OQ4; "because `<ClassName>` differ" reassurance dropped.
Assessment: §38 and OQ4 now aligned. Accept.

### requirements-7 — Fixed
Claim: AC9 "for any `A`/`B`" demands a mixed CST-vs-`self.cst` round-trip that the explicitly-out-of-scope `isinstance(item, self.cst.Item)` dispatch (fltk2gsm.py:69,80) makes unsatisfiable; consequence is wasted effort or license to touch out-of-scope dispatch. Verified against request ("does NOT eliminate self.cst isinstance dispatch") and exploration §182-195. Highest-impact finding.
Doc §91-92: AC9 retitled "label-compare backend independence" — now asserts only that label `==`/`in` inside `Cst2Gsm` succeed for same-denotation labels across backends, demonstrated by an isolated `A`-label vs `B`-constant check. Bound paragraph (citing §182-195) explicitly states AC9 does NOT claim mixed CST-vs-`self.cst` parity, full parity required only for the same-backend path. "for any `A`/`B`" / "no longer depend on backend matching" removed.
Assessment: matches the reviewer's narrowed AC9 exactly. Accept.

## Disputed items

None.

## Approved

7 findings: 7 Fixed verified. No Won't-Do, no TODO, no scope deferral.

---

## Verdict: APPROVED

All seven findings had real, source-backed consequences (doc clarity / soundness / scope-correctness); none bogus. Every Fixed disposition verified present and faithful in `requirements.md`. requirements-2 took a reviewer-offered option; the rest match the prescribed fixes.
