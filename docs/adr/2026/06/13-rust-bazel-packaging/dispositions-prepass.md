# Dispositions: prepass (slop + scope)

## slop-1

- Disposition: Fixed
- Action: `clockwork/dsl/clockwork_rust_roundtrip_test.py:24-26` — replaced the
  broad heuristic filter (`"span" in str(w.message).lower() or "fltk" in
  str(w.filename).lower()`) with a precise filter:
  `issubclass(w.category, UserWarning) and "fltk/fegen/pyrt/span" in w.filename`.
- Severity assessment: The reviewer's claim that `str(w.message)` returns the
  object repr is factually wrong in Python (`str()` on a `Warning` instance
  returns the message text, not the repr), so there was no false-negative risk
  from that half of the filter.  The overly broad `w.filename` check was real
  but benign in the failing direction (it would match the span.py path correctly;
  false positives from other fltk files would only cause the test to fail, not
  to pass vacuously).  Nonetheless the tighter filter by category and exact
  module path is strictly more correct and applied.

## slop-2

- Disposition: Fixed
- Action: `clockwork/dsl/clockwork_rust_roundtrip_test.py:3-13, 21` — replaced
  the module docstring (which cited design §5, AC #3 + #4 and gave
  implementation rationale) with one sentence describing what the test validates;
  replaced the function docstring (which explained fltk internals) with a single
  sentence stating the invariant being checked.  Design-doc references removed.
- Severity assessment: Cosmetic / maintenance.  Section numbers and AC IDs rot
  as the design doc evolves; a later reader has no reliable way to locate the
  cited document.  No runtime effect.

## slop-3

- Disposition: Fixed
- Action: `rust.bzl:39-41` (now removed) — the three-line inline comment
  restating the load-bearing fixed-basename constraint was a verbatim duplicate
  of the text already in the rule's `doc` string (lines 112-113 in the original,
  now at 109-110).  Deleted the inline copy; the `doc` string is the canonical
  reference for rule users.
- Severity assessment: Minor.  Duplicate comments diverge over time; removing
  the inline copy leaves the constraint documented in exactly one authoritative
  place.

## scope (pre-pass)

- Disposition: Won't-Do (no action needed)
- Action: no change
- Severity assessment: The scope reviewer found no missing design items.
  All design sections are accounted for in the implementation.  No findings
  to address.
