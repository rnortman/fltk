# Judge verdict — deep review (round 2)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base a2822d5..HEAD 1e67ed4. Round 2 — APPROVED or ESCALATE only.
Notes: 7 reviewer files. Round-1 verdict (`judge-verdict-deep.md`) issued REWORK on a single item: correctness-1. All other findings were accepted in round 1 and are unchanged at HEAD (the only new commit since 534e779 is 1e67ed4, scoped to genparser.py + fltk_cst_protocol.py + dispositions). This round re-walks only the disputed item.

## Disputed item (re-walked): correctness-1

Reviewer claim: committed `fltk_cst_protocol.py:1` reads `# ruff: noqa: N802`; generator (genparser.py) emitted `# ruff: noqa: N802, F821`. Artifact stale vs generator (design "Grammar drift" mandates lockstep).
Reviewer consequence: process-level — future `genparser generate` rewrites line 1 → spurious diff; "committed == generator output" untrue today. Real, non-blocking → should-fix.
Reviewer's suggested fix: regenerate so header becomes `# ruff: noqa: N802, F821`.

Round-1 disposition was a false "Fixed" (claimed the two-flag header was present when it was not) → REWORK.

Round-2 disposition (commit 1e67ed4): reverses direction. Root-caused that `make fix`/ruff strips F821 as RUF100 (unused noqa) because F821 never fires on the generated module; therefore drops F821 from the *generator template* (genparser.py:203 → `"# ruff: noqa: N802\n"`), regenerates, commits. Lockstep achieved by making the generator match the committed single-flag header rather than the reverse.

Evidence (HEAD 1e67ed4, empirically verified):
- Committed header: `# ruff: noqa: N802`. Generator template at genparser.py:203: `"# ruff: noqa: N802\n"`. Both single-flag — match.
- **Lockstep proven by regeneration**: rebuilt the extension, regenerated `fltk_cst_protocol.py` from the committed generator. Output is **byte-identical** to the committed file both pre-`make fix` and post-`make fix` (`diff` empty). No spurious diff on regen — the exact failure mode the reviewer flagged is gone.
- **Responder's RUF100 root cause is true**: injected the reviewer's preferred two-flag header `# ruff: noqa: N802, F821` and ran `ruff check --select RUF100` → flagged "Unused `noqa` directive". So the reviewer's literal suggested fix (re-add F821) would have reintroduced the churn; the responder's inverse fix is the correct one.
- **No protection lost**: stripped the noqa entirely and ran `ruff check --select F821` on the generated body → "All checks passed". F821 genuinely never fires under the project's ruff config; dropping it from the template forfeits nothing.
- pyright over `fltk_cst_protocol.py` + `fltk2gsm.py`: 0 errors. `test_cst_protocol.py` + `test_plumbing.py`: 52 passed.

Assessment: the round-1 REWORK basis is fully resolved. The new disposition is a genuine, stable fix — generator and artifact are in byte-for-byte lockstep, the root cause is correctly identified and empirically confirmed, and the chosen direction (drop F821) is strictly better than the reviewer's literal suggestion (which RUF100 would churn). "Fixed" is now accurate. Accept.

## Other findings

Not re-walked — all accepted in round 1 and untouched by commit 1e67ed4. test-5's comment-misattribution nit (noted in round 1, never part of the REWORK basis) remains a nit, not a blocker. test-6 (Fixed) was present in dispositions at round 1 and is unaffected.

## Approved

14 findings carried from round 1: 8 Fixed verified (errhandling-1, errhandling-2, test-1 through test-4, quality-2, quality-3, quality-5), 1 Won't-Do sound (errhandling-3), 3 TODOs acceptable (reuse-1+2 → `cst-protocol-generator-refactor`, quality-1 → `parse-result-typed`, quality-4 → `cst-protocol-label-free`), 1 Fixed-with-nit-comment (test-5), plus test-6 Fixed. Security/efficiency: no findings.
**correctness-1 now Fixed and verified** this round.

---

## Verdict: APPROVED

The sole round-1 REWORK item (correctness-1) is resolved. The updated disposition fixes the generator/artifact divergence in the correct direction: regeneration now yields a byte-identical committed file (verified empirically), the F821→RUF100 root cause is confirmed, and dropping F821 forfeits no real lint protection. All other dispositions stand from round 1. HEAD 1e67ed4.
