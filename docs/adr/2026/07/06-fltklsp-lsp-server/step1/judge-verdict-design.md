# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/06-fltklsp-lsp-server/workflow/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 4 findings, all dispositioned Fixed.
Doc phase — no TODO walk.

Source spot-checks performed before walking findings (all confirmed):
`gsm2parser.py:829` raises raw `NotImplementedError` for `INLINE` items;
`gsm2parser_rs.py:879-881, 1065-1067` likewise reject `INLINE`;
`fltk2gsm.py:113-122` gives rule invocations an implicit label equal to the rule name and
defaults unlabeled Literal/Regex to `SUPPRESS`; `gsm2parser.py:848`
(`if item.disposition != gsm.Disposition.SUPPRESS`) gates only child emission;
`Makefile:255` carries the "fltk.fltkg is intentionally broken" comment. LSP 3.17's
predefined `SemanticTokenTypes` set indeed lacks `punctuation`, `text`, `constant`, `label`.

## Findings walk

### design-1 — Fixed
Claim: the design directed the implementer to build INLINE-splicing terminal tables, an
inline-recursing validation path, and an "invoked solely with `!`" warn against parser
behavior that does not exist — `gsm2parser.py:828-830` raises `NotImplementedError` on any
`INLINE` item, so all of it would be unreachable, untestable dead code, and the real
behavior for a `!` grammar was an unhandled crash. Consequence real; blocker-severity for a
design doc.
Evidence in the fixed design:
- §4.4 new paragraph "**`INLINE` (`!`) is different and out of scope.**" —
  `prepare_analysis_grammar` scans for `INLINE` up front and raises a clean formatted
  error; cites `gsm2parser.py:828-830`, the Rust generator, and the Makefile comment (all
  verified above).
- §4.4 also fixes the falsified "nothing else" claim: the disposition-doesn't-affect-
  matching statement is now explicitly scoped "For `SUPPRESS`/`INCLUDE`".
- §4.3 item 2 recursion is now `Sequence[Items]` sub-expressions only — no INLINE mention.
- The old item-8 warn is gone; replaced by the note after rule 7 ("No dead-anchor warning
  is needed in round 1 ... `INLINE`-bearing grammars are rejected outright before
  validation runs").
- §4.5: terminal tables "precomputed from each rule's own items ... `INLINE` never arises
  — §4.4 rejects it."
- §6 INLINE bullet now describes the clean up-front rejection, not spliced-terminal
  classification.
- §7 carries the roadmap note: inline-aware classification needs its own design round
  if/when `gsm2parser` gains `INLINE` support.
- §8 `test_analysis.py` includes the rejection test ("clean unsupported-`INLINE` error,
  not a raw `NotImplementedError`").
Grepped the design for residual splicing language: none remains.
Assessment: reviewer's suggested fix adopted in full and consistently propagated through
every section the finding named. Accept.

### design-2 — Fixed
Claim: §2.4's compatibility rationale ("strictly more permissive, so it can be tightened
later without breaking") was inverted — under CLAUDE.md's out-of-tree-consumer standard,
tightening union semantics later would reject previously-valid `.fltklsp` files, which is
exactly the breaking direction. Consequence real (a future round could introduce the
ambiguity error believing it safe).
Evidence: §2.4 as it now stands contains no "can be tightened later" sentence. It rests on
the substantive rationale (implicit labels make ambiguity the norm — verified at
`fltk2gsm.py:114-115`; readings coincide except under explicit relabeling; the spec's rule
would make nearly every rule-name anchor an error) and closes with the explicit reversal:
"union semantics is itself a commitment: ... tightening to the spec's error rule later
would reject previously-valid files — a breaking change under this project's compatibility
standard — so this choice is being made deliberately, not as a reversible default."
Assessment: the inverted argument is gone and the correct direction is stated. Accept.

### design-3 — Fixed
Claim: the default layer could emit overlapping intervals of different types (nested
trivia nodes both painting `comment`; `prefix:"//"` inside a comment defaulting to
`operator`), making the §4.6 non-overlapping invariant unsatisfiable with no within-layer
precedence rule — and the plausible wrong implementer guess produces visibly wrong
highlighting that the §8 dogfood test would hit. Consequence real; blocker-severity.
Evidence:
- §4.5 trivia bullet: "**The default walk does not descend into `is_trivia_rule`
  nodes**: the outermost trivia node emits at most one `comment` interval, and its subtree
  contributes no further defaults" — with both collision cases named (nested
  `Trivia`/`LineComment` double-paint; `prefix:"//"` repainting as `operator`), and
  explicit paints inside trivia still applying per painter rule 1.
- §4.6 layer 2: "Default intervals are disjoint by construction: terminal spans under one
  parent don't overlap, and the trivia non-descent rule (§4.5) removes the only nesting
  source — so no within-layer precedence is needed." I checked this argument: default
  emitters are terminal spans (leaves, pairwise disjoint) and trivia nodes; CST spans
  either nest or are disjoint, and non-descent eliminates the nesting case. The
  disjointness claim holds.
- §8 `test_classify.py` includes the pinning case: "trivia non-descent: `//` inside a
  structured comment stays `comment`, never `operator`."
Assessment: rule adopted, invariant now satisfiable and argued, test added. Accept.

### design-4 — Fixed
Claim: §4.5's parenthetical listed only `punctuation`/`text` as non-LSP-standard legend
members; `constant` and `label` are also absent from LSP 3.17's predefined set, and
`constant` matters because the spec's clockwork example paints tokens `constant`.
Should-fix severity.
Evidence: §4.5 parenthetical now reads "Four legend members — `punctuation`, `text`,
`constant`, `label` — are not in LSP 3.17's predefined `SemanticTokenTypes`" and adds
"`constant` matters in practice: the spec's clockwork worked example paints
`boolean`/`unit_identifier` as `constant`, so M2/theme docs must account for it."
Assessment: exactly the correction requested, with the practical note. Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED

All four dispositions are sound: each fix is present in the design text, consistent across
every section the finding touched, and grounded in source facts I independently verified.
