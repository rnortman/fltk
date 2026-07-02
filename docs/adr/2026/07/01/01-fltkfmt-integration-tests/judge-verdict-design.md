# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-fltkfmt-integration-tests/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings. Base `c03a801` (confirmed = current HEAD).

## Other findings walk

(Doc phase — no added-TODOs walk.)

### design-1 — Fixed
Claim: §2.2 Test 1 as originally specified asserted all 16 corpus×config cases idempotent, but `rust_parser_fixture.fltkg × 40/4` is not idempotent under the current binary; consequence is an implementer dead end (the design forbade behavior changes AND required all tests green before TODO closure) plus an unsurfaced formatter bug.
Independent verification: I reproduced the claim myself against the existing debug binary — pass 1 ≠ pass 2, pass 2 == pass 3 (pass-2 fixed point). Reviewer's finding and responder's reproduction are both factually correct.
Fix in revised design: §2.2 Test 1 now carries a "Known exception, verified against the current binary (full 8×2 sweep run)" block that names the exact case, pins `out2 != out1` and `out3 == out2` so a future formatter fix trips the assertion, and rules out silent corpus shrinkage. §2.3 adds the paired `TODO(formatter-group-idempotency)` (comment + `TODO.md` entry). §3 gains the "Known non-idempotent case going stale" bullet. §4 item 1 documents the exception. §5 surfaces the bug to the user as the first visibility item with the alternative (fix formatter first, drop carve-out) named.
On the new planned TODO deferral: the bug is pre-existing (not created by this iteration), it is loudly surfaced to the user rather than silently deferred, and fixing formatter layout is a behavior change to both backends governed by cross-backend parity — genuinely a design-cycle decision, not something a test-addition iteration can do unilaterally. Deferral bar met.
Assessment: fix addresses the consequence completely and follows the reviewer's suggested options (a)+(b). Accept.

### design-2 — Fixed
Claim: §1 and §2.3 cited `TODO.md:93-95`, stale from an exploration done at `8fd5ecf`; at `c03a801` the file is 61 lines with the section header at line 51, so the directive pointed past EOF.
Verification: `grep -n 'fltkfmt-integration-tests' TODO.md` → line 51; `wc -l` → 61. Reviewer correct.
Fix in revised design: §1 now cites "the `## fltkfmt-integration-tests` section in `TODO.md`" (no line numbers); §2.3 directs deletion "located by its slug header (line numbers drift with unrelated TODO churn; the header is the stable anchor)". Exactly the reviewer's suggested fix.
Assessment: accept.

### design-3 — Fixed
Claim: Test 2 pins `-w 80 -i 2` explicitly but the documented regeneration command omitted the flags, so it floats with CLI defaults — the self-healing instruction breaks in precisely the defaults-change scenario the pinning guards against, producing a regenerate-fail loop.
Fix in revised design: the §2.2 Test 2 regeneration command now reads `... fltk/fegen/fegen.fltkg -w 80 -i 2 > crates/fltkfmt/tests/golden/fegen.fltkg.golden`, with the note that the explicit flags keep the regen command in lockstep with the test's pinned config.
Assessment: internal inconsistency removed at the cited spot. Accept.

## Approved

3 findings: 3 Fixed verified, 0 Won't-Do, 0 TODOs deferred as dispositions.

---

## Verdict: APPROVED

All three dispositions verified against the revised design and, where empirical, against the repository and the current binary. No disputed items.
