# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-span-selector-broken-native-diagnostic/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings.

## Findings walk

### design-1 — Fixed
Claim: design pinned to stale base 8fd5ecf and cited the TODO.md entry at line 77; at
HEAD c03a801 the entry lives at line 35. Consequence (low): implementer navigating by
line number lands in the wrong place in `TODO.md`.
Verification: `git log` confirms HEAD is c03a801. `grep -n` puts
`## span-selector-broken-native-diagnostic` at `TODO.md:35`. Design header (design.md:4-6)
now cites base c03a801 and notes the exploration-era drift as TODO.md renumbering only.
Both former line-77 references are corrected: "Root cause / context" (design.md:24, "header
at `TODO.md:35`") and "### TODO.md" (design.md:53-54), the latter additionally instructing
to locate the entry by slug rather than line number — matching the reviewer's suggested
fix exactly.
Assessment: fix addresses the finding at both cited spots. Accept.

### design-2 — Fixed
Claim: test plan said "follow the existing save/restore pattern" without stating why the
exact pattern is load-bearing — cleanup must restore the saved original `fltk._native`
module object, never delete-and-reimport, because a second genuine native import panics
(PyO3 `PanicException`, a `BaseException`). Consequence: a slightly-deviating implementer
gets a crash in `finally` that masks the test outcome and poisons module state for later
tests; all three new tests manipulate `sys.modules["fltk._native"]`.
Verification of the underlying facts: `src/lib.rs:21` carries
`.expect("UNKNOWN_SPAN already set; module initialized twice")` on `UNKNOWN_SPAN.set`,
so a double init does panic. The existing safe pattern is real:
`tests/test_span_protocol.py:36-39` restores the captured module object via
`sys.modules.update(saved)` before its restorative reload.
Verification of the fix: design.md:112-121 now states the constraint explicitly — restore
the saved original object before the restorative reload, never
`sys.modules.pop("fltk._native", None)` + fresh reimport — with the panic message,
`src/lib.rs:21` cite, the `BaseException` escape property, and a pointer to the existing
safe cleanup as the template ("follow that exactly"). The "Test-induced reload state"
edge-case bullet (design.md:91-99) cross-references the same constraint, as the
disposition claims.
Assessment: fix is the reviewer's suggested sentence and more, placed where the
implementer will read it. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED

Both dispositions verified against the design doc and source at HEAD c03a801. No
Won't-Do or TODO dispositions; nothing disputed.
