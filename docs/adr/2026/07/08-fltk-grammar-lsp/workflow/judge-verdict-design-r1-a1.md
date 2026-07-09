# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/08-fltk-grammar-lsp/workflow/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer-r1.md`); 5 findings. Dispositions: all Fixed.

## Findings walk

### design-1 — Fixed
Claim: two divergent regeneration paths for `requirements_lock.txt`; consequence is either `@pypi//pygls` never materializes (stretch-goal `py_binary` dead on arrival) or the committed lock's format/provenance churns undesigned.
Verification: `requirements_lock.txt:1-2` header confirmed verbatim (`uv export --format requirements-txt --no-editable --output-file requirements_lock.txt`). Design stretch step 1 (design.md:168-183) now declares the `uv export ... --extra lsp ...` command canonical, keeps `args = ["--extra", "lsp"]` on the Bazel `lock` target as a divergence guard, and states explicitly "its output is not what gets committed; the `uv export` command above is."
Assessment: fix names the canonical command, covers the reviewer's `--extra lsp` sub-point, and makes the format/provenance decision explicit. Accept.

### design-2 — Fixed
Claim: sketched def/ref kind `rule` is out of legend, so def-site and resolved-reference paints fall through to `variable`; test plan item 2's "rule-name def paint" could not pass; consequence is a silently undesigned decision on the most user-visible surface.
Verification: legend gating confirmed against source — `lsp_config.py` emits the declaration `Paint` only `if def_stmt.kind[0] in TOKEN_LEGEND`; `classify.py` documents out-of-legend refs contribute nothing; `features.SEMANTIC_TOKEN_TYPES` contains `type` and no `rule` (and no `regexp`, matching the cleanup note). Design section 1 now uses `type` everywhere (`def name: type` design.md:40-41, `ref rule:identifier: type` :42-44, `def rule_name: type` for unparsefmt :64 and the fltklsp extension :77) with a "Kind choice" bullet (:47-52) citing the gating lines and both precedents. Test plan item 2 pins "`type` with the `declaration` modifier" (:260); item 7 matches (:281-282).
Assessment: internally consistent now; kind choice is a designed decision with rationale. Accept.

### design-3 — Fixed
Claim: "five sidecar specs" should be six; consequence minor (reader could infer one file intentionally excluded from the wheel).
Verification: design.md:209 reads "three grammars and six sidecar specs (four new in section 1 + two existing)"; :213-217 clarifies the wheel-verification list is the five files that exist today, with the four new sidecars guarded by test plan item 1. Count independently checks: 4 new + 2 existing = 6.
Assessment: accept.

### design-4 — Fixed
Claim: test plan item 6 spawned the console script, but the cited harness deliberately uses `sys.executable -m`; consequence is FileNotFoundError under stale editable installs and CI/local divergence.
Verification: `test_server_crossfile.py:64` confirmed using `sys.executable`. Design test plan item 6 (:273-280) now spawns `[sys.executable, "-m", "fltk.lsp.grammar_cli", "fltkg"]` and explains why; section 2 (:124-126) specifies the `if __name__ == "__main__": app()` guard (confirmed present in `server_cli.py:79-80` as the cited precedent), noting it also serves the Bazel `py_binary`. Console-script name coverage delegated to item 5, stated at :279-280.
Assessment: fix follows the suggested pattern exactly, including the `__main__` guard corollary. Accept.

### design-5 — Fixed
Claim: "lazy start serializes typical startups" overstated the Bazel lock mitigation — VS Code session restore opens multiple clients in one activation tick, making contention the default multi-file case; consequence docs-level (README would mislabel the common failure mode as unlikely).
Verification: design.md:197-205 now states contention "is the *expected* case, not a corner," explains session restore, notes Bazel queues on the lock (symptom: slow/timed-out startups, not corruption), and promotes `--script_path` to "the primary recommendation whenever more than one fltk language is in use, not as an escape hatch." Edge-cases bullet (:240-242) agrees. No residual "mitigated by lazy start" claim anywhere in the doc (lazy start is retained only for its legitimate purpose — process count, :148-150, :238-239).
Assessment: accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified.

---

## Verdict: APPROVED

All five dispositions verified against the revised design and against source at 9473bf9. No TODOs, no Won't-Dos; every fix is present, correctly sourced, and internally consistent with the test plan.
