# Dispositions: design review round 1 — rust-generated-ident-collisions

Style: concise, precise, no padding. Audience: smart LLM/human.

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (same dir). All findings fact-checked against `fltk/fegen/gsm.py`, `fltk/fegen/gsm2tree_rs.py`.

design-1:
- Disposition: Fixed
- Action: §3 trivia-annotation paragraph rewritten — annotation keyed on auto-addition (`gsm.TRIVIA_RULE_NAME not in grammar.identifiers` on the raw pre-augmentation `grammar` arg, still in scope in `__init__`), not on the rule name. Edge-cases bullet updated (user-defined `_trivia` reported as ordinary rule). Test plan item 2 gains both annotation cases.
- Severity assessment: Verified real (`gsm.py:422-426` returns grammar unchanged when user defines `_trivia`). Without the fix, the feature's core deliverable — an actionable diagnostic — lies to users who wrote `_trivia`.

design-2:
- Disposition: Fixed
- Action: Test plan item 2, emitted-only positive case — absence assertion changed to `pub enum FooLabel {` (with trailing brace), with the `FooLabelLabel` substring hazard explained inline.
- Severity assessment: Verified — the helper builds labeled rules by default, so `foo_label` emits `pub enum FooLabelLabel`, which contains the bare substring. The brace-less assertion would fail spuriously on the design's key positive test, inviting a weakening "fix" during implementation.

design-3:
- Disposition: Fixed
- Action: §3 reserved-names bullet rewritten to state the real invariant (no reserved name starts with `Py` or ends with `Child`/`Label`), and to require recording it as a constraint in the comment above `_RESERVED_CLASS_NAMES` so future Py-prefixed additions know to seed `claims`.
- Severity assessment: Verified — the original `Py{CN}`-case-argument was wrong (`Py{CN}` = R iff R = "Py" + CN; CN case irrelevant). Conclusion held for the current set, but a maintainer adding e.g. `PySpan` would have trusted a false invariant and silently lost coverage.

design-4:
- Disposition: Fixed
- Action: "Proposed approach" preamble qualified — byte-identical output only for grammars that remain accepted; the one newly rejected previously-compiling class (`drop_worklist_item` rule, no node-typed children) is named and cross-referenced to §1.
- Severity assessment: Verified contradiction — `_drop_block` returns `""` for flat grammars (`gsm2tree_rs.py:1936-1937`), so such a grammar compiles today and §1 newly rejects it. Risk was downstream reviewer confusion and the implementer misreporting the change as fully non-breaking; the conservative choice itself is request-directed and unchanged.
