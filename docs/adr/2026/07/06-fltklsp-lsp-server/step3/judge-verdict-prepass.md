# Judge verdict — step3 M4 pre-pass

Phase: pre-pass (slop + scope). Base 1ad3141..HEAD 8966d8e. Round 1.
Notes: `notes-prepass-slop.md`, `notes-prepass-scope.md`. Dispositions: `dispositions-prepass.md`.

Both reviewers report "No findings"; the dispositions doc records that faithfully (no code
changes, no commit — correct for a no-findings round). With nothing to disposition, the
adjudication question is whether either no-findings verdict is bogus (lazy review). Spot-checked
both against the diff.

## Added TODOs walk

No TODO-dispositioned findings, and independently verified: `git diff 1ad3141..8966d8e`
(excluding docs) adds **zero** new `TODO(slug)` comments. The only slug touches are extensions
of pre-existing slugs:

- `TODO(lsp-classify-hotpath)` comment at `fltk/lsp/classify.py:400-402` — extended in the diff
  to note symbol extraction as the third O(tree) walk, exactly per design §4.4 ("part of the
  same planned unification, not a new TODO").
- `TODO(lsp-rule-surface-index)` — referenced by design §4.1 as the eventual absorber of the
  `GrammarTables`/`rule_for_node` promotion; no new comment added.

No TODO.md entries required; scope reviewer's "no TODO.md gap" claim verified.

## No-findings verification walk

### Scope reviewer — accepted, verified
Claim: all three log increments present, matching design §2.1–2.6/§4.1–4.6; all M4 items plus
the two authorized §2.5 additions delivered; no undesigned work.

Spot-checks against the diff:
- Diff stat matches the design §3 deliverables table exactly: `symbols.py` new (+304),
  `lsp_config.py`, `classify.py`, `engine.py`, `features.py`, `server.py`, six test files,
  `test_data/greet.fltkg`/`.fltklsp`, plus the implementation log. Nothing outside `fltk/lsp/`
  + step3 docs — no plumbing/fegen/Rust/packaging churn, per §3.
- `engine.py` diff read in full: `DocumentAnalysis.symbols: SymbolTable | None = None`
  (additive keyword default), `analyze()` runs `symbols.extract` inside the existing
  `RecursionError` guard and threads the table into `classify(..., symbol_table=...)` —
  line-for-line §4.6.
- Ref-paint interval shape in the log (`(ref.start, ref.end, Paint(token=symbol.kind[0],
  modifiers=()), (ref.depth, ref.tier))`) matches §4.4 verbatim; entering before
  `_winner_segments` preserves precedence machinery as designed.
- Three commits in range (da4ce07, 0f5dbb8, 8966d8e) map 1:1 to the log's three increments.
- Log's three recorded deviations checked against design text: (a) rename refusal via
  `JsonRpcException` — design §2.6 says "fails with an error message" without prescribing a
  mechanism; within bounds. (b) capabilities read per-request from `self.client_capabilities`
  instead of captured at initialize — session-fixed values, semantically identical, avoids
  overriding pygls's `initialize`; within bounds. (c) `document_symbols` stack holds children
  lists, not nodes — implementation detail below design altitude. All three properly logged.

Assessment: the no-findings scope verdict is substantiated, not lazy. Accept.

One nuance checked and ruled acceptable: design §4.4 says the "existing `TODO(lsp-classify-hotpath)`
**entry** is extended"; the implementation extended the code *comment* (`classify.py:400-402`),
not the `TODO.md` entry (TODO.md untouched). The design's intent — record the third walk inside
the existing unification TODO rather than minting a new one — is satisfied; the note is durable
and colocated at the exact fold point a burndown reader will visit from TODO.md. Not a scope gap.

### Slop reviewer — accepted
Claim: no findings (diff-only thin pass).

Spot-checks: 1830 added lines scanned for LLM tells — no changelog-style comments ("used to",
"was renamed", "previously"), no workflow-doc restatements, no dead scaffolding. Two test-file
section-divider comments carry design-section references ("Ref-site paint (§4.4)" at
`test_classify_painter.py:154`, "Namespace hoist (§2.1)" at `test_symbols.py:152`). Noted, not
blocked: the descriptive half of each header stands alone, and the identical pattern
("design §4.1", `test_fltklsp_parse.py:155`) is pre-existing, review-accepted precedent from the
prior step — flagging the same convention now would be inconsistent, and the deep pass's quality
review is the right venue if the project wants the convention retired. Nit at most.

Assessment: no-findings slop verdict holds. Accept.

## Disputed items

None.

## Approved

0 findings; both no-findings reviews verified against the diff; dispositions doc accurate.

---

## Verdict: APPROVED

Commit at HEAD: 8966d8ee42840c5f7fbf26090b14ef20eafc28e0.
