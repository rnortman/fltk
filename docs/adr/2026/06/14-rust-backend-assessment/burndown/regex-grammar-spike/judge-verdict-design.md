# Judge verdict — regex-grammar-spike (design phase)

Phase: design. Doc: `burndown/regex-grammar-spike/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 5 findings, all dispositioned Fixed.
(Design phase — no added-TODOs walk.)

## Other findings walk

### design-1 — Fixed
Claim: the design asserts in five places (§1.2, §2, §5 Inc-1 acceptance, §6, §7) that `make check` enforces a no-drift gate on the committed `regex_*` artifacts. Consequence: an implementer trusting a non-existent drift gate could commit a stale or hand-edited `regex_parser.py` that lints clean, silently breaking the spike's central "the grammar compiles through FLTK's generator" claim.
Source check: `Makefile:39-51` — `check-common` runs exactly `lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-python-features cargo-test-no-python cargo-clippy-no-python check-no-pyo3`; `gencode` is a standalone target (`Makefile:247`) not in the `check`→`check-ci`→`check-common` graph; the `git diff --stat` "drift" line is a human-facing comment after a *manual* `make gencode` (`Makefile:245-246`). Reviewer correct; consequence is real.
Disposition check (design text): §1.2 now carries a "What `make check` does and does not enforce" paragraph reproducing the exact step list and stating gencode is manual + not in the graph (lines 83-94). §2 reworded to "manual drift-detection step ... not a CI-enforced gate" (lines 143-147). §5 Inc-1 acceptance split into (a) clean-only, (b) manual `make gencode` + `git diff` regen-match, (c) artifacts import (lines 466-470). §6 "Generated parser drifting" bullet rewritten with the explicit warning "the implementer must not assume `make check` will catch a stale or hand-edited `regex_parser.py`. It will not." (lines 541-548). §7 bullet retitled "Generated-artifact cleanliness gate," states clean-only, no drift gate (lines 574-578).
Assessment: fix addresses the consequence at every named site; the false promise is removed and the residual manual step is correctly located. Accept.

### design-2 — Fixed
Claim: §4.1's planned REJECT-offset assertion (`longest_parse_len ≥ 0 and ≤ len(pattern)`) is unsound. Consequence: a guaranteed-broken test in the Opus increment that is supposed to be the rigorous one — either non-compiling (unreadable through `parse_text`) or flaky (tracker at `-1`).
Source check: `plumbing_types.py:26-32` — `ParseResult` exposes only `cst/terminals/success/error_message`; no `error_tracker`, so `longest_parse_len` is unreadable through `parse_text(...).success`. `errors.py:25` — `ErrorTracker.longest_parse_len` defaults to `-1`, advanced only by `fail_literal`/`fail_regex`. `plumbing.py:323` — `parse_text` rejects on `result.pos != len(terminals.terminals)`; a short-parse reject records no terminal failure, so the tracker can legitimately sit at `-1`. Reviewer correct on both blocking facts.
Disposition check (design text): §4.1 oracle bullet now states "**No `longest_parse_len` assertion**," walks both blocking facts with the exact citations, and confines any future offset check to the direct `apply__parse_regex(0)` path asserting only `<= len(pattern)` (lines 338-351). Propagated to §3.2 ("diagnostic only, never an assertion target," lines 231-234) and §6/§7.
Assessment: the unsound assertion is removed and the design now correctly identifies accept/reject as the sole robust signal. Fix matches the consequence. Accept.

### design-3 — Fixed
Claim: §4.1's Python `re` cross-check is asymmetric — sound for ACCEPT, near-useless for REJECT. Consequence: the dangerous over-admission direction (a REJECT case that is actually portable) is unguarded; an Opus-authored REJECT case with a wrong Rust-divergence rationale passes silently, masking a real over-rejection finding — exactly the "fool the parser" point the suite exists for.
Source check: `re.compile` on `[a-z-0]`, `a{`, `{`, `\07` all succeed on Python (verified by running). The suite has no inline Rust oracle (O3 deferred), so the REJECT clause's "Python accepts AND Rust accepts" can never be evaluated. Reviewer correct; consequence is real and is the spike's load-bearing value claim.
Disposition check (design text): §4.1 cross-check bullet rewritten "ASYMMETRIC; ACCEPT-only" — states the cross-check is "effectively useless and must not be relied on" for REJECT, names the over-admission direction as "unguarded by any automated cross-check," routes REJECT correctness to the mandatory rationale string (now required to state the *Rust-side* basis), and surfaces O3(b) as the only thing that would make the REJECT cross-check real, escalated to the user (lines 352-368). §5 Inc-4 bullet updated so it no longer implies the cross-check validates REJECT cases (line 500).
Assessment: the false "honest rather than circular" framing is corrected; the residual judgement-call nature of REJECT cases is stated plainly and the real fix (O3(b)) is correctly raised as a user decision rather than silently dropped. Accept.

### design-4 — Fixed
Claim: §3.4's snapshot helper reinvents the §3.1 GSM walk; O4 leaves its form under-specified. Consequence (minor): two copies of the non-trivial sub-expression-recursing walk could drift, silently producing a stale or mismatched clockwork snapshot.
Source check: `gsm.py:291-302` — `_for_each_item` already performs the depth-first item walk including sub-expressions; the helper's core enumeration is identical to the corpus test's collector. Reviewer correct; consequence real but low-severity (a duplication/drift risk, not a correctness failure in the design as such).
Disposition check (design text): §3.4 now mandates the helper "call the exact same `collect_regexes(grammar)` collector the corpus test uses (§3.1) — single source of truth for the GSM walk," with the helper's only added responsibilities being the out-of-tree read and the JSON provenance header (lines 296-302). O4 narrowed to "entry-point packaging only (script vs make target)" (lines 623-627).
Assessment: single-source-of-truth is now mandated; the open question is reduced to a genuine ergonomics preference. Fix matches the (minor) consequence. Accept.

### design-5 — Fixed
Claim: §5's "Each independently committable" overstates Inc 3, which extends Inc 2's `tests/test_regex_grammar_corpus.py` and reuses Inc 2's collector. Consequence (low): an orchestrator could read "independently committable" as license to reorder/parallelize Inc 3 ahead of Inc 2, which would fail on the hard file/function dependency.
Source check: design §5 Inc 3 bullet 2 ("Extend `test_regex_grammar_corpus.py`") and §3.1 (shared collector) confirm the dependency. Reviewer correct; consequence real and low.
Disposition check (design text): §5 header rewritten with an explicit dependency summary — "Inc 2 and Inc 4 each depend only on Inc 1; Inc 3 depends on Inc 1 *and* Inc 2 ... not independently committable from Inc 2 and must not be reordered before it" (lines 453-458). Inc 3 dependency line updated (lines 492-494); §5 closing reworded to "committable in dependency order" (line 516).
Assessment: the misleading framing is removed and the true dependency edge is stated explicitly. Fix matches the consequence. Accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified (design-1 through design-5), each fix located in the design text and source-confirmed. Reviewer's findings all carry a stated consequence justifying the edit; no bogus-reviewer push-back warranted (every load-bearing source claim — `check-common` step list, `ParseResult` fields, `ErrorTracker` default, the four Python `re` acceptances, the `_for_each_item` walk — independently confirmed).

---

## Verdict: APPROVED

All five dispositions acceptable. Each finding had a real, source-backed consequence; each Fixed edit lands in the design text and addresses that consequence. No over-claimed fixes, no hand-wavy deferrals, no bogus findings.
