# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/06-rust-cst-child-span-test/design.md`. Round 1.
Notes: `notes-design-design-reviewer.md` (1 reviewer file, 3 findings). Dispositions: `dispositions-design.md`. Ground truth checked at HEAD af6e6f3.

## Findings walk

### design-1 — stale TODO.md line numbers — Fixed (incomplete)

Claim: design cited `TODO.md:39` / `:44-46` for the span-test and identity entries; actual headings are at `TODO.md:35` and `:40`. Consequence: Cleanup instruction by line number misdirects an implementer toward deleting (part of) the live `rust-cst-child-node-identity` entry.

Verified at HEAD: `TODO.md:35` = `## rust-cst-child-span-test` (paragraph :37); `TODO.md:40` = `## rust-cst-child-node-identity` (paragraph :42). The three flagged citations are corrected:
- design.md:13 → `TODO.md:40-42` (identity) — correct.
- design.md:37 → `TODO.md:35-37` (span-test) — correct.
- design.md:92 → locate-by-slug at line 35, entry 35-37, explicit do-not-touch for identity at line 40 — correct.

Incomplete: design.md:66 still cites `TODO.md:44-46` for the clone-on-extraction identity TODO. At HEAD, lines 44-46 are the `## gencode-poc-fltkg` entry. Same defect class as the finding (stale TODO.md number pointing at the wrong entry), and it now contradicts the corrected citation at design.md:13 (`TODO.md:40-42`) for the same entry. The disposition's "corrected all three citations" covers only the reviewer-quoted lines; the doc retains the defect.

Assessment: fix incomplete → REWORK item. One-line correction.

### design-2 — misplaced `==`-precedent citation — Fixed

Claim: design.md:66 cited `tests/test_fegen_rust_cst.py:148-155` (body of a different test); the mirrored roundtrip test is `test_append_and_child_roundtrip` at 132-139.

Verified at HEAD: design.md:66 now names `test_append_and_child_roundtrip` and cites `tests/test_fegen_rust_cst.py:132-139`. Grep confirms: `def test_append_and_child_roundtrip` at line 132, clone-on-extraction `==` comment at 138, assert at 139. Citation exact.

Assessment: fix verified. Accept.

### design-3 — missing `# noqa: E402` on new import — Fixed

Claim: design's instruction "Add `from fltk._native import Span, SourceText`" omitted the `# noqa: E402` every post-`importorskip` import requires; verbatim implementation passes pytest but fails `make check`.

Verified at HEAD: design.md:41 now spells `from fltk._native import Span, SourceText  # noqa: E402`, states the suppression is mandatory (importorskip at line 29 precedes imports), and cites the neighboring imports at lines 34-39. Grep confirms `importorskip` at `tests/test_phase4_fegen_rust_backend.py:29` and all six imports at 34-39 carrying `# noqa: E402`.

Assessment: fix verified. Accept.

## Disputed items

- **design-1**: residual stale citation at design.md:66 — `TODO.md:44-46` is the `gencode-poc-fltkg` entry at HEAD; the identity entry is `TODO.md:40-42` (as design.md:13 correctly states). Need: correct design.md:66 to `TODO.md:40-42` (or cite by slug only).

## Approved

2 findings: 2 Fixed verified (design-2, design-3).

---

## Verdict: REWORK

design-1's fix is incomplete — the flagged defect class (stale TODO.md line number pointing at the wrong entry) persists at design.md:66, contradicting the corrected citation at design.md:13. Round 1.
