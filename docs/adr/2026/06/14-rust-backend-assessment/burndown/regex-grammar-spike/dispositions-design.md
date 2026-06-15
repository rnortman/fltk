# Dispositions: regex-grammar-spike design review (round 1)

Reviewer notes: `notes-design-design-reviewer.md`. Design: `design.md`.
All five findings fact-checked against source (Makefile, plumbing.py, plumbing_types.py,
pyrt/errors.py) and one empirically verified by running the generated parser. The reviewer's
own end-to-end validation (all predicted dispositions confirmed) is corroborated; the findings
target specific load-bearing false/under-specified claims, all accepted.

---

design-1:
- Disposition: Fixed
- Action: Rewrote the "gated by `make check` / drift gate" language everywhere it appeared.
  §1.2 gained a new "What `make check` does and does not enforce" paragraph stating the exact
  `check-common` step list (`Makefile:39-51`) and that `gencode` is a standalone manual target
  not in the check graph, so regen-match is a manual `make gencode` + `git diff` step. §2
  reworded the `gencode` contract as a manual drift-*detection* step, not a CI gate. §5
  Increment-1 acceptance split into (a) `make check` = clean only, (b) manual `make gencode` +
  `git diff` = regen-match, (c) artifacts import. §6 "Generated parser drifting" bullet and §7
  "Generated-artifact gate" bullet both rewritten to say `make check` enforces cleanliness, not
  up-to-date-ness, and warn the implementer not to rely on it to catch stale/hand-edited
  artifacts.
- Severity assessment: The design promised an automated drift gate that does not exist; an
  implementer trusting it could ship a stale or hand-patched `regex_parser.py` undetected,
  silently breaking the spike's central "the grammar compiles through FLTK's generator" claim.

design-2:
- Disposition: Fixed
- Action: Removed the `longest_parse_len ≥ 0` REJECT-offset assertion. §4.1 oracle bullet now
  states two blocking facts: (1) `ParseResult` (`plumbing_types.py:26-32`) carries only
  `cst/terminals/success/error_message` — not `error_tracker` — so `longest_parse_len` is
  unreadable through the `parse_text(...).success` oracle; (2) `ErrorTracker.longest_parse_len`
  defaults to `-1` (`errors.py:25-48`) and the dominant short-parse reject records no terminal
  failure, so `≥ 0` is not guaranteed and would flake. The spike asserts only accept/reject.
  Any future offset check must use the direct `apply__parse_regex(0)` path and assert only
  `<= len(pattern)`. Propagated to §3.2 and §6 (offset is now "diagnostic only, never an
  assertion target") and §7 (adversarial bullet: "no `longest_parse_len` assertion").
  Empirically confirmed the short-parse mechanism: `a**`→pos 2, `a{`→pos 1, `[a-z-0]`→pos 0,
  `[[:alpha:]]`→pos 0, all `success=False` via `result.pos != len`.
- Severity assessment: As written the assertion was either non-compiling (unreadable through
  `parse_text`) or flaky (tracker at `-1`), and it sat in the Opus increment that is supposed
  to be the rigorous one — a guaranteed-broken test.

design-3:
- Disposition: Fixed
- Action: Rewrote the §4.1 cross-check bullet as "ASYMMETRIC; ACCEPT-only." It now states the
  Python `re` cross-check catches ACCEPT mis-specs but is effectively useless for REJECT
  (the suite's REJECT cases are overwhelmingly "Python accepts, Rust diverges"; `[a-z-0]`,
  `a{`, `{`, `\07` all `re.compile` cleanly — verified), so the dangerous over-admission
  direction is unguarded by any automated check. REJECT correctness now explicitly rests on the
  mandatory `rationale` string, which must state the *Rust-side* basis. Tied the only real fix
  (O3(b) cargo helper) to user judgement. Updated the §5 Inc-4 bullet so it no longer implies
  the cross-check validates REJECT cases.
- Severity assessment: The original framing claimed the cross-check kept expectations "honest
  rather than circular," but for the bulk of the suite (REJECT cases, the whole "fool the
  parser" point) it was still circular — a wrong Rust-divergence rationale would pass silently,
  masking a real over-rejection finding.

design-4:
- Disposition: Fixed
- Action: §3.4 now mandates the snapshot helper call the *same* `collect_regexes(grammar)`
  collector the corpus test uses (single source of truth for the GSM walk), reimplementing
  nothing; its only added responsibilities are reading the out-of-tree path and emitting the
  JSON provenance header. O4 narrowed to "entry-point packaging only (script vs make target)."
- Severity assessment: Minor. Left as-was, an implementer could write a second copy of the
  non-trivial sub-expression-recursing walk in the helper, and the two copies could drift,
  silently producing a stale or mismatched clockwork snapshot.

design-5:
- Disposition: Fixed
- Action: Rewrote the §5 header to give an explicit dependency summary — Inc 2 and Inc 4 depend
  only on Inc 1; Inc 3 depends on Inc 1 *and* Inc 2 (shares the corpus module + collector) and
  is not independently committable. Updated the Inc 3 dependency line and the §5 closing
  sentence (was "committable on its own") to "committable in dependency order."
- Severity assessment: Low. The wrong "independently committable" framing could lead an
  orchestrator to reorder or parallelize Inc 3 ahead of Inc 2, which would fail because Inc 3
  edits Inc 2's file and imports its collector.
