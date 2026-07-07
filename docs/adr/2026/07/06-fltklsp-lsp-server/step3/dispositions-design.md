# Dispositions — step3 design review, round 1

Findings: `notes-design-design-reviewer.md`. Design revised in place:
`docs/adr/2026/07/06-fltklsp-lsp-server/step3/design.md`. Every finding was fact-checked
against source before dispositioning; all five verified and all five are Fixed.

design-1:
- Disposition: Fixed
- Action: §6 `test_dogfood.py` bullet rewritten. Verified against
  `fltk/lsp/fltklsp.fltklsp` (28 lines): it contains only `scope` statements — the
  reviewer is right that the "existing def/ref/namespace statements" the old bullet
  activated do not exist (the constructs the current dogfood suite exercises live in the
  *sample input text*, not the spec). Fix takes the finding's option (b): the committed
  public example stays untouched (a symbol vocabulary for the `.fltklsp` language itself —
  e.g. whether repeated `rule X {}` blocks each "define" X — is called out as its own
  future design decision), and the test loads a purpose-built test-local spec against the
  real `fltklsp.fltkg` grammar.
- Severity assessment: as written the test was unimplementable; the implementer would
  either drop the round's only real-grammar end-to-end semantic check or improvise an
  undesigned semantic change to a public example file.

design-2:
- Disposition: Fixed
- Action: §4.5 `document_symbols` now specifies the nesting pass runs over symbols sorted
  by `(range_start, -range_end)`, with the trailing-name counterexample recorded inline
  (declaration ranges are laminar CST spans; `name_start` order breaks the stack when a
  container's def anchor follows its members). `SymbolTable.symbols` stays
  name-start-ordered for the lookup helpers, per the finding's fix. §6 `test_features.py`
  bullet gains the name-anchor-after-members nesting test.
- Severity assessment: silent wrong outlines for legal grammar shapes (members surfacing
  as siblings of their container), and the original test plan would naturally have missed
  it because name-first constructs make the two orderings coincide.

design-3:
- Disposition: Fixed
- Action: §4.1 gains a decision bullet: `classify._GrammarTables` and `_rule_for_node`
  are promoted to public `GrammarTables` / `rule_for_node` as the shared rule-resolution
  surface for `classify` and `symbols`; `symbols.extract`'s `tables` parameter is that
  type, and extraction's uses (matcher-lookup keying, node-child rule names for
  `match_applies`, `is_trivia_rule`) are enumerated. The §3 file-layout row for
  `classify.py` records the promotion. Verified: both names are `_`-private
  (`classify.py:64, 162`) and `engine.py:86` already carries `_GrammarTables` across the
  module boundary, so the promotion ratifies de-facto usage; the eventual
  `TODO(lsp-rule-surface-index)` unification absorbs this surface later.
- Severity assessment: without the decision, the design's own layering rule (the stated
  justification for moving the match predicate) was violated by its own `extract`
  signature, forcing the implementer to pick the new public module boundary by accident.

design-4:
- Disposition: Fixed
- Action: §2.6 gains a third bullet: when the client advertises
  `workspace.workspaceEdit.documentChanges` (captured at initialize), rename returns
  `documentChanges` with a `TextDocumentEdit` versioned via
  `OptionalVersionedTextDocumentIdentifier` to the analyzed document version; plain
  `changes` is the fallback, with the residual race confined to clients that cannot
  express versioned edits. Propagated to §4.5 (`rename_edits` packaging), §4.6 (handler +
  capability capture), §5 (new rename-racing-a-keystroke edge case), and §6
  (`test_server.py` asserts both payload shapes). Verified: the handler pattern in
  `server.py` awaits the worker via `run_in_executor` (twice for rename), so a
  `didChange` can interleave on the loop; `_GoodAnalysis.version` already exists to
  supply the version.
- Severity assessment: a rename racing a keystroke could garble the document client-side —
  the exact corruption mode §2.6's own rationale names as disqualifying — with no
  server-side guard able to see it.

design-5:
- Disposition: Fixed
- Action: §2.1's decision wording harmonized to the rule-level condition ("a symbol whose
  `def` is anchored in a rule that is a namespace rule"), matching §4.2's extraction rule
  and the resolved `namespace_rules: frozenset[str]`, with an explicit note that
  namespace-ness is a property of the rule (blocks accumulate; the split-block spelling
  hoists identically; block identity is deliberately erased at resolution). Verified:
  `RuleBlock.is_namespace` is per-block (`lsp_config.py:102-109`) and multiple blocks per
  rule are legal and pinned (`test_multiple_rule_blocks_accumulate`), so the two prior
  wordings genuinely diverged on split-block specs.
- Severity assessment: the round's load-bearing scoping rule had two non-equivalent
  readings; the block-level reading reproduces the exact go-to-def failure §2.1 exists to
  prevent whenever a spec splits `def` and `namespace` across blocks.
