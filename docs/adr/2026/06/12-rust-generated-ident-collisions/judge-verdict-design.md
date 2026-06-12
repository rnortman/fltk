# Judge verdict — design review

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/12-rust-generated-ident-collisions/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 4 findings, all dispositioned Fixed. Doc phase — no TODO walk.

## Findings walk

### design-1 — Fixed
Claim: §3 keyed the `_trivia` "auto-generated" annotation on the rule name alone; `gsm.add_trivia_rule_to_grammar` returns the grammar unchanged when the user defines `_trivia` (verified in source: `if TRIVIA_RULE_NAME in grammar.identifiers: return grammar`, `gsm.py:425`). Consequence: diagnostic falsely tells a user their own `_trivia` is auto-generated — real, since the feature's whole point is an actionable message.
Design now: §3 annotation paragraph keys on auto-addition (`gsm.TRIVIA_RULE_NAME not in grammar.identifiers` on the raw pre-augmentation `grammar` arg, design.md:69); edge-cases bullet covers user-defined `_trivia` reported as ordinary rule (design.md:86); test plan item 2 includes both annotation cases (design.md:103).
Assessment: fix addresses claim and consequence at the named section, with test coverage added. Accept.

### design-2 — Fixed
Claim: emitted-only positive test's "no `pub enum FooLabel`" substring assertion is unsound — helper builds labeled rules by default, so `foo_label` emits `pub enum FooLabelLabel`, which contains the bare substring. Consequence: the key positive test fails spuriously or gets weakened during implementation.
Design now: test plan item 2 asserts absence of `pub enum FooLabel {` with the trailing brace and explains the `FooLabelLabel` substring hazard inline (design.md:102). Matches the reviewer's first suggested fix.
Assessment: assertion is now sound (`pub enum FooLabel {` cannot be a substring of `pub enum FooLabelLabel {`). Accept.

### design-3 — Fixed
Claim: justification for not seeding reserved names into `claims` rested on a false `Py{CN}` case argument; real invariant is that no reserved name starts with `Py` or ends with `Child`/`Label`. Consequence: future maintainer adding e.g. `PySpan` trusts a false invariant and silently loses coverage.
Design now: §3 bullet states the real invariant over the five named reserved names, notes direct `CN`-vs-reserved is covered by the existing per-rule check (verified present in `__init__`, `gsm2tree_rs.py:80-83`), and requires recording the invariant as a constraint in the comment above `_RESERVED_CLASS_NAMES`, explicitly flagging that a future Py-prefixed entry must be seeded into `claims` (design.md:75).
Assessment: false reasoning replaced with the correct invariant plus a forward-looking guard. Accept.

### design-4 — Fixed
Claim: "no generated-output change for grammars that generate today" contradicted §1's deliberate rejection of `drop_worklist_item` in flat grammars (verified: `_drop_block` returns `""` when child union is empty, so such grammars compile today). Consequence: downstream reviewers hit an apparent contradiction; implementer may misreport the change as fully non-breaking.
Design now: preamble qualified — "no generated-output change for grammars that remain accepted. Exactly one previously-compiling class becomes newly rejected: a rule named `drop_worklist_item` in a grammar with no node-typed children anywhere (§1, request-directed ...)" (design.md:25).
Assessment: contradiction resolved; the newly rejected class is named and cross-referenced. The conservative choice itself is unchanged and request-directed. Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable; each fix verified in the updated design text and against cited source.
