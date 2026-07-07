# Dispositions — design review round 1

Design: `docs/adr/2026/07/06-fltklsp-lsp-server/workflow/design.md`
Notes: `docs/adr/2026/07/06-fltklsp-lsp-server/workflow/notes-design-design-reviewer.md`

All four findings were independently fact-checked against source before disposition.
Key verifications: `gsm2parser.py:828-830` does raise `NotImplementedError("Inline items
not yet supported...")` for any `INLINE` item; `gsm2parser_rs.py:879-881, 1065-1067`
likewise reject `INLINE`; `inline_to_parent` in `gsm2parser.py` is the sub-*expression*
splicing mechanism only (set per-term, unrelated to `Disposition.INLINE`); the Makefile
comment "fltk.fltkg is intentionally broken" exists at `Makefile:255`; and LSP 3.17's
predefined `SemanticTokenTypes` set indeed lacks `constant` and `label` as well as
`punctuation`/`text`.

design-1:
- Disposition: Fixed
- Action: Adopted the reviewer's suggested fix in full — INLINE-bearing target grammars
  are declared unsupported in round 1 with a clean up-front rejection, and all
  inline-splicing machinery is deleted from the design.
  - §4.4: new paragraph "**`INLINE` (`!`) is different and out of scope.**" —
    `prepare_analysis_grammar` scans for `INLINE` dispositions and raises a clean,
    formatted error instead of letting the generator's `NotImplementedError` escape.
    Also corrected the falsified "nothing else" claim: the disposition-doesn't-affect-
    matching statement is now scoped to `SUPPRESS`/`INCLUDE` only.
  - §4.3 item 2: removed the "and through `INLINE`-disposition invocations" recursion.
  - §4.3 item 8 (the "invoked solely with `!`" warn): deleted entirely, replaced with a
    note explaining why no dead-anchor warning is needed in round 1 (suppressed subtrees
    surface as real nodes in the analysis grammar; INLINE grammars are rejected before
    validation).
  - §4.5: terminal tables no longer "include the terminals of transitively `INLINE`d
    rules"; they are built from each rule's own items.
  - §6: the INLINE edge-case bullet now describes the clean rejection, not spliced-
    terminal classification.
  - §7: roadmap follow-up added — inline-aware classification needs its own design round
    if/when `gsm2parser` gains INLINE support.
  - §8: `test_analysis.py` gains a test that an `!`-bearing grammar produces the clean
    unsupported error, not a raw `NotImplementedError`.
- Severity assessment: High for the design as written — it directed the implementer to
  build unreachable, untestable machinery (no `!` grammar can produce a parser to test
  against) while the real behavior for such grammars was an unhandled crash, violating
  the design's own error-reporting standards.

design-2:
- Disposition: Fixed
- Action: §2.4 rewritten. The inverted sentence ("strictly more permissive, so it can be
  tightened later without breaking existing files") is gone; the section now rests on the
  substantive rationale alone (ambiguity is the norm under implicit labels; readings
  coincide except under explicit relabeling; the spec's error rule would make the
  language unusable) and explicitly states that union semantics is itself a commitment —
  tightening later would reject previously-valid out-of-tree `.fltklsp` files, a breaking
  change under this project's compatibility standard.
- Severity assessment: Medium-high despite being one sentence — a freeze-rationale
  document for public-API surface containing an inverted compatibility argument invites a
  future round (M4 or later) to introduce the ambiguity error believing it is safe,
  breaking downstream files. The reviewer's direction analysis is correct: valid-then-
  rejected is the breaking direction.

design-3:
- Disposition: Fixed
- Action: Adopted the reviewer's suggested rule verbatim in substance. §4.5 trivia bullet
  now states the default walk does not descend into `is_trivia_rule` nodes — the
  outermost trivia node emits at most one `comment` interval and its subtree contributes
  no further defaults — with both collision cases (nested trivia nodes; `prefix:"//"`
  repainting as `operator` inside comments) named as the motivation, and explicit paints
  inside trivia still applying per painter rule 1. §4.6 layer 2 now states that default
  intervals are disjoint by construction (sibling terminal spans don't overlap; trivia
  non-descent removes the only nesting source), so no within-layer precedence exists.
  §8 `test_classify.py` gains the trivia non-descent case (`//` inside a structured
  comment stays `comment`, never `operator`).
- Severity assessment: High — as specified, the non-overlapping token-stream invariant
  was unsatisfiable and the most plausible implementer guess (terminal defaults win)
  produces visibly wrong highlighting (`//` painted `operator` inside every comment),
  which the §8 dogfood test would hit immediately since `.fltklsp` comments are
  structured trivia.

design-4:
- Disposition: Fixed
- Action: §4.5 parenthetical corrected to list all four non-LSP-3.17-standard legend
  members (`punctuation`, `text`, `constant`, `label`), and now notes that `constant`
  matters in practice (the spec's clockwork worked example paints
  `boolean`/`unit_identifier` as `constant`), so M2/theme documentation must account for
  it.
- Severity assessment: Low-to-medium — no round-1 behavioral impact, but an M2 designer
  taking the old parenthetical at face value would register the wrong custom-type set and
  clockwork's `constant` tokens would silently go uncolored in default VS Code theming.

Post-disposition: cleanup-editor pass applied to the design (smoothed the edited
passages, removed a redundancy introduced in §2.4; no substantive changes beyond the
dispositions above).
