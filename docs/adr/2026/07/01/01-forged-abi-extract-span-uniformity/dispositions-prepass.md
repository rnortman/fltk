# Dispositions — prepass, round 1

slop-1:
- Disposition: Fixed
- Action: Dropped the "(forged-abi-extract-span-uniformity design)" parenthetical from the `TestForgedSpanRejected` class docstring (tests/test_rust_span.py:1093). The "Mirrors TestForgedSourceTextRejected" sentence carries the intent.
- Severity assessment: Cosmetic. A shipped test docstring pointed at an ephemeral design slug / a TODO entry deleted by this same diff, giving a future reader nothing to resolve it against. No behavioral impact.

slop-2:
- Disposition: Fixed
- Action: Rephrased "The exploration §4 scenario end-to-end" to "The end-to-end forge scenario" in `test_forged_span_via_reassignment_raises_type_error` (tests/test_rust_span.py:1114). The rest of the docstring already describes the scenario concretely.
- Severity assessment: Cosmetic. Comment referenced an offstage EDTC exploration document by section number, meaningless to anyone without that doc. No behavioral impact.

## Scope notes
notes-prepass-scope.md: "No findings." Nothing to disposition.
