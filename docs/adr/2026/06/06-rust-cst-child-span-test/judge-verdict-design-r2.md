# Judge verdict — design review, round 2

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/06-rust-cst-child-span-test/design.md`. Round 2 (APPROVED or ESCALATE only).
Notes: `notes-design-design-reviewer.md`. Dispositions: `dispositions-design.md`, `dispositions-design-r2.md`. Prior verdict: `judge-verdict-design.md` (REWORK on design-1 residual). Ground truth checked at current tree (HEAD 9fc55b5; see note below).

## Findings walk

Round-2 scope: the single disputed item (design-1 residual at design.md:66). design-2 and design-3 were verified-Fixed in round 1 and are not re-litigated; spot-checks below confirm their citations still hold at the current tree.

### design-1 — stale TODO.md citation at design.md:66 — Fixed (completed)

Prior verdict's residual: design.md:66 cited `TODO.md:44-46` for the clone-on-extraction identity TODO; at the tree under review, 44-46 is the `## gencode-poc-fltkg` entry, contradicting the corrected citation at design.md:13.

Verified at current tree:
- `grep -n '^## ' TODO.md`: `rust-cst-child-span-test` heading at :35 (entry 35-37), `rust-cst-child-node-identity` at :40 (entry 40-42), `gencode-poc-fltkg` at :44.
- design.md:66 now cites `TODO.md:40-42` — correct, and consistent with design.md:13.
- Grep of all `TODO.md:` citations in design.md: exactly three (line 13 → `40-42`, line 37 → `35-37`, line 66 → `40-42`). All verified correct; no stale citation remains; doc is internally consistent. The Cleanup section (design.md:92) locates by slug with an explicit do-not-touch for the identity entry — the misdirection consequence is fully retired.

Assessment: residual fixed; fix complete. Accept.

### Spot-check of round-1-approved fixes (not re-walked)

- design-2: `def test_append_and_child_roundtrip` at `tests/test_fegen_rust_cst.py:132`, clone-on-extraction `==` comment at :138; `CLASS_LABEL_INFO` at :43. design.md:66's citation `132-139` correct.
- design-3: design.md:41 spells `# noqa: E402` with rationale; `importorskip` at `tests/test_phase4_fegen_rust_backend.py:29`, post-skip imports at :34-39 all carry the suppression, TODO comment at :111-113. Correct.

## Note: repo advanced under the design

The repo moved af6e6f3 → 9fc55b5 during the review cycle (3055a3e deleted the `test-class-is-type-body` TODO entry, −4 lines in `TODO.md`, −16 in `tests/test_fegen_rust_cst.py`). The design's header still says "HEAD af6e6f3", but every line citation in the doc matches the **current** tree — the tree the implementer will work in. The label/citation mismatch is cosmetic, affects no instruction, and does not block: all load-bearing references are correct where it counts. Not a REWORK-grade defect, and round 2 offers no REWORK in any case.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified (design-1 across two rounds, design-2, design-3).

---

## Verdict: APPROVED

The round-1 residual (design.md:66) is corrected and all `TODO.md` citations in the design are accurate and mutually consistent against the current tree. All dispositions acceptable.
