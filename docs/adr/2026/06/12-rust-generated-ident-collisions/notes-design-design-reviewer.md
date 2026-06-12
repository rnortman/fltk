# Design review findings: rust-generated-ident-collisions

Style: concise, precise, no padding. Audience: smart LLM/human.

Verified against `fltk/fegen/gsm2tree_rs.py`, `fltk/fegen/gsm2tree.py`, `fltk/fegen/gsm.py`, `fltk/iir/py/naming.py`, `TODO.md`, `tests/test_gsm2tree_rs.py` (working tree == base b02cb8f). All cited line numbers in the design check out (reserved check at gsm2tree_rs.py:80-83, handle f-string at :709, `_label_enum_block` empty-return at :470-471, `_drop_block` guard at :1936, `DropWorklistItem` enum at :1946, generate loop at :289-296, `rule_models` populated in `CstGenerator.__init__` at gsm2tree.py:43-44, non-injective `snake_to_upper_camel` at naming.py:7-13, existing test conventions at tests/test_gsm2tree_rs.py:1542-1582 with 3-tuple parametrize matching the proposed `drop_worklist_item` entry). Requirements coverage is complete: all four collision classes, error naming both rules + identifier, raise-before-emission, DropWorklistItem reserved entry, byte-identical output for valid grammars, TODO removal, test expectations. Findings below are refinements, not blockers.

## design-1 — `_trivia` annotation mislabels a user-defined `_trivia` rule

Section: §3, "When a claimant is the auto-added trivia rule, annotate it as `rule '_trivia' (auto-generated trivia rule)`".

What's wrong: the design keys the annotation on the rule name alone, but `_trivia` is not always auto-added. `gsm.add_trivia_rule_to_grammar` returns the grammar unchanged when the user already defines `_trivia` (`fltk/fegen/gsm.py:425`: `if TRIVIA_RULE_NAME in grammar.identifiers`). A user-written `_trivia` participating in a collision (e.g. user rules `_trivia` + `trivia`, both CN `Trivia`) would be annotated "auto-generated", which is false.

Consequence: misleading diagnostic in a feature whose entire purpose is an actionable message; a user who wrote `_trivia` is told the colliding rule is one they never wrote.

Suggested fix: `RustCstGenerator.__init__` still has the raw pre-augmentation `grammar` argument in scope; annotate only when `gsm.TRIVIA_RULE_NAME not in grammar.identifiers`.

## design-2 — Emitted-only positive test's "no `pub enum FooLabel`" assertion is unsound as a substring check

Section: Test plan item 2, "Emitted-only positive case: `foo` built with an **unlabeled** item + `foo_label` → accepted; `generate()` output contains `pub struct FooLabel` ... and no `pub enum FooLabel`".

What's wrong: the same test-plan item says the multi-rule helper builds rules with "labeled regex items ... by default", so rule `foo_label` itself has labels and emits its own label enum `pub enum FooLabelLabel` (`_label_enum_rust_name`, gsm2tree_rs.py:454; emission at :494). The string `pub enum FooLabel` is a substring of `pub enum FooLabelLabel`, so a naive `"pub enum FooLabel" not in src` assertion fails spuriously even though the emitted-only behavior is correct.

Consequence: the key positive test for the design's central judgment call (emitted-only semantics) fails for the wrong reason, or gets "fixed" during implementation in a way that weakens what it asserts.

Suggested fix: assert absence of `pub enum FooLabel {` (with the brace), or build `foo_label` with an unlabeled item too so no `FooLabelLabel` exists.

## design-3 — Incorrect justification for not seeding reserved names into `claims` (conclusion holds)

Section: §3, design decision bullet: "derived non-`CN` identifiers cannot equal any current reserved name (`{CN}Child`/`{CN}Label` end in `Child`/`Label`; **`Py{CN}` would require `CN` to start lowercase, impossible** ...)".

What's wrong: the `Py{CN}` argument is not the real reason. `Py{CN}` equals a reserved name R iff R starts with `Py` and R[2:] is a derivable CN; CN case is irrelevant. The actual invariant: none of the five reserved names (`NodeKind`, `Span`, `Shared`, `CstError`, `DropWorklistItem`) starts with `Py`, ends with `Child`, or ends with `Label`. The conclusion (no coverage gap, no duplicate reporting) is correct for the current set; the stated reasoning is wrong.

Consequence: a future maintainer adding a Py-prefixed reserved name (e.g. a `PySpan` wrapper) would trust a false invariant and silently lose collision coverage for `Py{CN}` vs reserved.

Suggested fix: state the real invariant; optionally note it as a constraint on future `_RESERVED_CLASS_NAMES` additions in the code comment.

## design-4 — "No generated-output change for grammars that generate today" overstates; §1 deliberately rejects one previously-working class

Section: "Proposed approach" preamble: "no generated-output change for grammars that generate today" vs §1: "a rule named `drop_worklist_item` is rejected even in a grammar where the enum would not be emitted (no node-typed children anywhere)".

What's wrong: a grammar with a rule `drop_worklist_item` and no node-typed children generates today and its output compiles (`_drop_block` returns `""`, gsm2tree_rs.py:1936-1937; exploration confirms class 5 errors only when the enum is emitted). §1 makes such a grammar newly rejected. The preamble's blanket compatibility claim and §1's documented conservative choice contradict each other. The choice itself is fine — request.md explicitly directs adding `DropWorklistItem` to the reserved set, and the design documents the trade-off.

Consequence: downstream reviewers (scope/correctness) fact-checking the compatibility claim against §1 hit an apparent contradiction; the implementer may also misreport the change as fully non-breaking.

Suggested fix: qualify the preamble: "no generated-output change for grammars that remain accepted; the only newly rejected previously-compiling case is a `drop_worklist_item` rule in a flat grammar (§1, request-directed)".
