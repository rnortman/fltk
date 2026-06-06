# Dispositions — Cross-Backend Label Equality requirements review (round 1)

Reviewer notes: `notes-requirements-requirements-reviewer.md`. Each finding fact-checked against request intent + `exploration.md` before disposition.
Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

---

requirements-1 (perf "Pin" over-specifies mechanism):
- Disposition: Fixed
- Action: Constraints §Performance — deleted the "(Pin: precompute/intern...)" mechanism prescription; rewrote the bullet as a non-blocking SHOULD that explicitly leaves technique to design ("mechanism is design's call"), naming precompute/intern/static-`&'static str`/integer-keying as designer options. The Co-generation bullet's "equality computed from the canonical name each side already knows" is retained: it constrains the *key* (no shared registry), not a caching technique, so it is not a mechanism pin.
- Severity assessment: Medium. Left unfixed, the designer was boxed into intern/precompute against the request's explicit "mechanism is design's call," potentially excluding a cheaper zero-alloc static-string scheme.

requirements-2 (perf budget lacks falsifiable threshold):
- Disposition: Fixed
- Action: Constraints §Performance — resolved by downgrading perf to an explicit non-blocking design SHOULD with "no measured perf acceptance criterion," rather than inventing a coarse perf AC. This keeps the AC set correctness-only (AC1-9) and avoids a fabricated threshold ("X% of baseline") not grounded in request/exploration. Chosen the reviewer's second offered option, consistent with requirements-1.
- Severity assessment: Medium. An unenforceable "must not regress meaningfully" sitting among gated ACs invited a slow design to pass review while appearing constrained; explicit downgrade removes the false sense of a gate.

requirements-3 (symmetry needs Python-side override, not just Rust richcmp):
- Disposition: Fixed
- Action: Constraints §"Symmetry & non-raising" — added that BOTH generators must emit custom equality, that the Python `enum.Enum` identity `__eq__` must be overridden, and that the Python side must yield `NotImplemented` (not `False`) for foreign operands so the reflected Rust richcmp runs in the `py == rust` direction. Behavior was already correctly pinned by AC1/AC7; only the rationale was one-sided.
- Severity assessment: Medium. A Rust-only implementation following the prior §104 wording would silently fail AC1's `py == rust` direction (Python short-circuits before the reflected op), caught only at test time and easily mis-diagnosed.

requirements-4 (`NotImplemented` vs `False` conflated in §6/§56):
- Disposition: Fixed
- Action: System behavior §6 — constrained the parenthetical: `NotImplemented` is acceptable only where the correct answer is `False`; the equal case (§1/AC1) must return `True` as a value from at least one side, else both-`NotImplemented` falls back to identity and yields a wrong `False`.
- Severity assessment: Low. AC1 already forces the equal case to `True`, but the "equivalently" framing invited a uniform-`NotImplemented` design that breaks AC1 when both sides defer.

requirements-5 (premise: no current consumer triggers cross-backend path):
- Disposition: Fixed
- Action: Goals — added a "Premise" paragraph citing exploration §146/§178/§201-202/§218: all in-tree consumers are same-backend by construction; this work future-proofs the drop-in contract for external/mixed-backend consumers and is not fixing a present in-tree breakage; AC9 is a constructed demonstration, not a regression guard.
- Severity assessment: Medium. Without the premise, the work reads as fixing a live bug; this affects prioritization and risks over-investment (e.g. the perf pin) on false urgency.

requirements-6 (§38 definition contradicts OQ4 on cross-grammar collision):
- Disposition: Fixed
- Action: Definitions §"Denote the same grammar label" — rewrote to state plainly that canonical name is rule+label scoped and does NOT encode grammar identity, enumerating the same-grammar, distinct-rule-collision, and cross-grammar-collision cases; explicitly defers the cross-grammar collision acceptance to OQ4 and drops the "because `<ClassName>` differ" reassurance that implied grammar-level disambiguation.
- Severity assessment: Low-to-medium. A design built on the prior §38 framing ("ClassName disambiguates grammars") would have a silent soundness hole if two grammars' CSTs coexist; low practical likelihood but genuine.

requirements-7 (AC9 "for any A/B" unachievable given out-of-scope isinstance dispatch):
- Disposition: Fixed
- Action: Acceptance criteria AC9 — narrowed. AC9 now asserts only that label comparisons (`==`, `in`) inside `Cst2Gsm` succeed across backends for same-denotation labels (demonstrated by an isolated `A`-label vs `B`-constant check), and adds an explicit Bound (citing exploration §182-195) that AC9 does NOT claim mixed CST-vs-`self.cst` round-trip parity because the unchanged `isinstance(item, self.cst.Item)` dispatch (out of scope per request) returns `False` for foreign-backend nodes. Full `Cst2Gsm` parity is required only for the same-backend path. Removed the overstated "for any `A`/`B`" / "no longer depend on backend matching" framing.
- Severity assessment: High. As written, AC9 demanded an unsatisfiable mixed-backend round-trip; a designer would either waste effort on it or read it as license to touch the explicitly-out-of-scope isinstance dispatch.

---

All seven findings validated against sources and applied; none required Won't-Do or TODO promotion. Open questions section unchanged in count (OQ4 referenced by the requirements-6 fix but already present).
