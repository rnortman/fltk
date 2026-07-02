# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-unparser-none-path-diagnostics/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings, all dispositioned Fixed.

## Other findings walk

(No TODO dispositions; design phase, TODO walk omitted.)

### design-1 — Fixed
Claim: header stated `Base commit: 8fd5ecf` while citing `TODO.md:43-45`, a locator only true at `c03a8012`; consequence is a verifier checking out the stated base finds the locator false and wrongly distrusts the design's other citations.
Doc inspection: `design.md:4-6` now reads "Base commit: `c03a8012`. TODO entry: `TODO.md:43-45`. (Exploration was written against `8fd5ecf`, where the same entry sat at `TODO.md:85-87`; all line references in this design are against `c03a8012`.)"
Independent source check: `grep -n` at HEAD (`c03a801`) shows the entry at `TODO.md:43`; `git show 8fd5ecf:TODO.md` shows it at `:85`. Both the reviewer's claim and the fix's parenthetical are accurate.
Assessment: fix addresses the consequence exactly — base commit corrected and the cross-commit locator discrepancy explained inline. Accept.

### design-2 — Fixed
Claim: test-plan item 5 targeted `tests/test_pyrt_errors.py`, a file whose docstring scopes it to `fltk.fegen.pyrt.errors` (cross-pinned with the Rust escape tests); consequence is a literal one-shot implementer appending an unrelated `fltk.unparse.pyrt` test there, muddying a documented cross-pinning contract.
Doc inspection: `design.md:233-237` (test plan item 5) now targets "new `fltk/unparse/test_pyrt.py`, alongside the other `fltk.unparse` tests" and carries an explicit warning: "(Not `tests/test_pyrt_errors.py` — despite the name, that file is scoped to `fltk.fegen.pyrt.errors` and cross-pinned with the Rust escape tests.)"
Independent source check: `tests/test_pyrt_errors.py` docstring reads exactly as the reviewer quoted ("Tests for fltk.fegen.pyrt.errors — escape_control_chars and format_error_message. Expected strings are cross-pinned with the Rust unit tests in crates/fltk-cst-core/src/escape.rs").
Assessment: fix matches the reviewer's suggested remedy (new `fltk/unparse/test_pyrt.py`) and inoculates a future reader against the name collision. Accept.

### design-3 — Fixed
Claim: the same `extract_span_text` call site was cited as `:1764` in "Context / root cause" and `:1758` in Proposed-changes §3; consequence negligible (both land in the right block), flagged for consistency only.
Doc inspection: §3 (`design.md:139`) now cites "the `extract_span_text` call (`:1764`)", matching the Context citation at `design.md:26` (`gsm2unparser.py:1764`).
Independent source check: `fltk/unparse/gsm2unparser.py:1764` is the `pyrt_module.method.extract_span_text.call(` line — `:1764` is the accurate locator for the call in both places.
Assessment: consistency cleanup done and accurate. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All three dispositions verified against the revised design and independently spot-checked against source. Reviewer findings were sound (consequences stated, all confirmed); responder fixes are complete and accurate. No dispositions disputed.
