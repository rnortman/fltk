# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-native-span-init-error-context/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings. Dispositions:
`dispositions-design.md`.

Doc phase — no added-TODOs walk.

## Findings walk

### design-1 — Fixed
Claim: Test plan enumerates updates only in `test_gsm2lib_rs.py`, but
`test_gen_rust_lib_span_only_output` in `fltk/fegen/test_genparser.py` asserts the exact
old use line; consequence is a red test in `make test`/`make check` for an implementer
following the plan verbatim, and a false "unchanged tests keep passing" claim.
Premise verified independently: `fltk/fegen/test_genparser.py:1565` asserts
`use span::{SourceText, Span};` inside `test_gen_rust_lib_span_only_output` (def at
line 1541). Severity: should-fix (plan-completeness defect that would block the
precommit gate mid-implementation).
Fix in doc: Test plan header now reads "Primarily in `fltk/fegen/test_gsm2lib_rs.py` ...
plus one CLI-level test in `fltk/fegen/test_genparser.py`"; the "Updated" list adds
`test_gen_rust_lib_span_only_output` with the use-line update, the
`m.add_class::<LineColPos>()` assertion, and the optional
`assert "LineColPos" not in src` mirror in `test_gen_rust_lib_standard_output`; the
closing claim is now scoped to "Remaining tests".
Assessment: fix addresses the consequence exactly, including both optional suggestions.
Accept.

### design-2 — Fixed
Claim: §1 consequence overstated on two axes — (a) a post-regen `LineColPos` drop would
not survive silently ( `make test` → `build-test-fixtures` → `build-native` rebuild plus
module-scope `from fltk._native import LineColPos` in `tests/test_rust_span.py`), and
(b) dropping `add_class` breaks the import/attribute surface, not `Span.line_col`
return values (pyo3 lazy pyclass creation). Consequence: the design doc is the durable
justification record; misrecording the safety net could later justify unnecessary
"we have no gate" work.
Premise verified independently: `tests/test_rust_span.py` does the module-scope
`from fltk._native import LineColPos` — a drop fails loudly at collection, post-rebuild.
Severity: should-fix (accuracy of the ADR-adjacent record; does not change what gets
built).
Fix in doc: §1 "Context / root cause" now states the divergence itself is invisible
until regen; post-regen the drop is caught loudly by `make test`/`make check` via the
`test_rust_span` import but only after a full native rebuild; the drift pin moves
detection to a pure-Python unit test; and it correctly narrows the breakage to the
attribute/import surface while noting returned `LineColPos` instances keep working.
Assessment: matches the reviewer's suggested framing on both sub-claims. Accept.

### design-3 — Fixed
Claim: two non-emitted description surfaces (`LibSpec.register_span_types` docstring,
`--register-span-types` CLI help) still say "Span/SourceText" and are absent from the
§1 change list; consequence is minor doc rot landing on the out-of-tree
`--register-span-types` edge case the design itself calls out.
Premise verified independently: `gsm2lib_rs.py:99` docstring and `genparser.py:789`
help text both read "Span/SourceText class registration". Severity: nit-to-should-fix
(two one-line doc updates, but directly on the consumer-facing story).
Fix in doc: §1 gains a fourth bullet covering both surfaces, and the "Proposed
approach" preamble notes the two description updates ride along, with the rationale
that the CLI help is how an out-of-tree user learns their `mod span;` must export
`LineColPos`.
Assessment: both surfaces covered. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All three dispositions are Fixed and each fix is present in the design doc and
addresses the finding's consequence; all finding premises independently re-verified
against source.
