# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-bazel-neg-test-harness/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings, all dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: header stated `Base commit: 8fd5ecf` while every line citation matches c03a801 (TODO.md entry at 59-61 vs. 109-111 at 8fd5ecf); consequence is an implementer cross-checking the stated base finds all citations off and distrusts or mis-edits.
Doc now (design.md:5-7): `Base commit: c03a801.` plus a parenthetical explicitly noting exploration.md was written at 8fd5ecf with differing line numbers (109-111 vs. 59-61 example included).
Independently verified at HEAD c03a801: TODO.md `## bazel-neg-test-harness` entry at lines 59-61; `_require_protocol_module` defined rust.bzl:32-41 with the exact coupling message; the macro-side call site and six-knob tuple loop with the exact per-knob message sit at rust.bzl:603/612-622; MODULE.bazel:5-6 lists only rules_python/rules_rust; BUILD.bazel:138-142 holds the `TODO(bazel-neg-test-harness)` comment. Citations and stated base now agree.
Assessment: fix addresses the consequence exactly; the parenthetical additionally defuses the exploration.md mismatch. Accept.

### design-2 — Fixed
Claim: §1 snippet pinned `version = "1.7.1"` while the adjacent instruction said "pin the current latest BCR release" — a self-contradiction built on an unverifiable external-registry claim; consequence is verbatim copying silently pins a stale version.
Doc now (design.md:69, 72-74): snippet reads `version = "<latest BCR release>"`, and the parenthetical says to substitute at implementation time because the latest release "is not verifiable from this repo, so no literal is pinned here."
Assessment: matches the reviewer's suggested fix verbatim; contradiction removed, no unverifiable literal remains. Accept.

### design-3 — Fixed
Claim: "Instantiating a rule via a struct attribute is legal" was asserted flatly despite being an external-Bazel-semantics claim with no in-repo precedent; consequence limited (pre-declared alias fallback) but implementer should verify first, not last.
Doc now (design.md:106-113): claim softened to "should be legal," explicitly flagged as "an external-Bazel-semantics claim with no in-repo precedent," with a bolded **verify it first** instruction (build the `neg_protocol_without_module` target's analysis before writing the rest of the suite) and the concrete fallback path (`generate_rust_srcs_for_testing` alias + adjust the §3 BUILD snippet).
Assessment: converts the risk into an early cheap check with a pre-declared fallback, exactly what the finding asked. Accept.

## Approved

3 findings: 3 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All three dispositions are Fixed and each fix is present in the doc and matches the finding's requested remedy; the corrected factual claims (base commit, line citations, file contents) were independently re-verified against the working tree at c03a801.
