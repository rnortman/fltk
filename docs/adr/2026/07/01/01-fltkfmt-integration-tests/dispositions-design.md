# Dispositions: design review round 1 (fltkfmt integration tests)

Findings from `notes-design-design-reviewer.md`. Each was independently re-verified before
disposition (base commit `c03a801`, debug binary rebuilt from source).

design-1:
- Disposition: Fixed
- Action: Independently reproduced the reviewer's claim — I ran the full 8×2 sweep myself
  against a freshly built debug binary: exactly one case is non-idempotent,
  `fltk/fegen/test_data/rust_parser_fixture.fltkg` at `w=40 i=4` (pass 1 emits the grouped
  alternation as a 2-line layout, pass 2 re-breaks it into a 4-line `(`…`)` block, pass 3
  == pass 2). All other 15 cases are idempotent. Design revised per the reviewer's
  suggested option (a)+(b) combined: §2.2 Test 1 now documents the known exception
  explicitly and carves it out — for that one case the test asserts `out2 != out1` and
  `out3 == out2` (convergence by pass 2), pinning today's behavior so a future formatter
  fix trips the assertion and forces carve-out removal. The formatter bug itself is
  surfaced: new `TODO(formatter-group-idempotency)` (comment at the carve-out + `TODO.md`
  entry, added to §2.3), and the discovery is flagged to the user in §5 as the first
  visibility item, with the alternative (fix the formatter first, drop the carve-out) named.
  §3 gains a matching edge-case bullet; §4 test-plan item 1 updated. No silent corpus
  shrinkage.
- Severity assessment: High. As written, Test 1 was guaranteed to fail on one case while
  the design simultaneously forbade every escape route (behavior changes out of scope, TDD
  note requiring all tests green before TODO closure) — a hard dead end for the
  implementer, plus an unsurfaced real formatter bug.

design-2:
- Disposition: Fixed
- Action: Verified: `grep -n` puts the `## fltkfmt-integration-tests` header at
  `TODO.md:51` and the file is 61 lines at `c03a801`; the design's `93-95` numbers were
  stale copies from the exploration (done at `8fd5ecf`, before the TODO-burndown commit
  shifted the file). Both citations fixed to reference the section by slug header instead
  of line numbers: §1 context cite and the §2.3 deletion directive (which now also notes
  why the header, not line numbers, is the anchor).
- Severity assessment: Low. The slug header uniquely identifies the section so an
  implementer recovers easily, but the directive pointed past EOF and line-number
  references would keep rotting with TODO churn.

design-3:
- Disposition: Fixed
- Action: Verified the inconsistency: the test pins `-w 80 -i 2` explicitly, while the
  documented regen command relied on CLI defaults (`FmtArgs` `default_value_t = 80` / `= 2`,
  `crates/fltk-fmt-cli/src/lib.rs:53-58`). §2.2 Test 2's regeneration command now includes
  `-w 80 -i 2`, with a note that the explicit flags keep the regen command in lockstep with
  the test's pinned config.
- Severity assessment: Medium. Harmless today (defaults match), but in exactly the
  defaults-change scenario the explicit test flags guard against, the failure message's
  self-healing instruction would regenerate the fixture at the wrong config, producing a
  persistent regenerate-fail loop.

All three findings resulted in design edits; the revised design was re-passed through the
cleanup-editor. No TODO-deferrals of findings and no Won't-Do dispositions.
