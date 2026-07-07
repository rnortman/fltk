# Design review findings — step3 (M4 def/ref/namespace semantics)

Design: `docs/adr/2026/07/06-fltklsp-lsp-server/step3/design.md` at 76124f9.
Verification basis: direct reads of `fltk/lsp/lsp_config.py`, `classify.py`, `engine.py`,
`server.py`, `features.py`, `fltklsp.fltkg`, `fltklsp.fltklsp`, `test_lsp_resolve.py`,
`test_dogfood.py`, and the cited step1/step2/spec/README lines.

Verified accurate (not repeated below): every code citation I checked resolves correctly —
`DefStmt`/`RefStmt`/`RuleBlock.is_namespace` (`lsp_config.py:88-109`), def/ref anchor
validation (`:430-433`), def-site paint (`:625-628`), the inertness docstring (`:604-606`),
`test_ref_and_namespace_are_inert` (`test_lsp_resolve.py:105-110`), `classify._matches`
(`classify.py:229-245`), trivia non-descent (`classify.py:183-188`), the empty-config
short-circuit (`lsp_config.py:646-647`), the formatting verify-reparse guard
(`server.py:373-417`), union-anchor semantics (`lsp_config.py:549-564`), the grammar's
restriction of def/ref/namespace to rule blocks (`fltklsp.fltkg:6-12`), `SOURCE_RANK_*`
values (`lsp_config.py:486-491`), and the step2 seam quote (`step2/design.md:559-562`).
The §2.1 hoist rationale, §2.4 degradation, and §5 silent-unresolved decisions are
internally sound and consistent with the advisory spec's evident intent.

---

## design-1 — §6 test plan: `fltklsp.fltklsp` has no def/ref/namespace statements

**Quote**: "`test_dogfood.py` — `fltklsp.fltklsp`'s existing def/ref/namespace statements
now exercised semantically: a sample spec's symbols extract and a reference resolves."

**What's wrong**: `fltk/lsp/fltklsp.fltklsp` (28 lines) contains only `scope` statements —
zero `def`, `ref`, or `namespace` statements (verified by grep; the file ends at
`rule literal { scope value: string; }`). The def/ref/namespace constructs the existing
dogfood suite exercises live in the *sample input text* being highlighted
(`test_dogfood.py:60`, `sample = "rule widget {\n  def alpha: ...`), not in the dogfood
spec itself. There are no "existing" statements to activate.

**Consequence**: the described dogfood test cannot be written as specified. The implementer
either silently drops the test (losing the round's only real-spec end-to-end semantic
check) or improvises an undesigned change: adding def/ref/namespace statements to the
committed `fltklsp.fltklsp` — a semantic decision the design never made (what is a
sensible symbol in the `.fltklsp` language itself? `def rule_name` on `rule_config` blocks
would create duplicate defs for every repeated block, interacting with the design's own
duplicate-def rules). Since `.fltklsp` files are public-facing examples, that spec file
change deserves a deliberate design decision, not a test-time improvisation.

**Fix**: either (a) specify the exact statements to add to `fltklsp.fltklsp` (and their
intended semantics), or (b) reword the test to use a purpose-built sample spec/grammar
pair, dropping the "existing statements" claim.

## design-2 — §4.5: containment stack over name-start-ordered symbols computes wrong nesting

**Quote**: "Nesting is by **declaration-range containment** computed with a stack over
document-ordered symbols"; §4.2 defines document order as "by `name_start`"
(`symbols: tuple[Symbol, ...]  # all symbols, document order (by name_start)`).

**What's wrong**: a containment stack is only correct over symbols sorted by *range* start
(declaration ranges are CST node spans, hence properly nesting — laminar). Sorting by
`name_start` breaks it whenever a construct's def anchor appears *after* nested member
defs in source: e.g. a rule shaped `outer := "{" , member* , "}" , "as" , name:ident`
(trailing-name / alias shapes are legal grammar). There, the member symbol's `name_start`
precedes the outer symbol's `name_start`, so the stack sees the inner symbol first; when
the outer symbol arrives, the inner is already popped/placed and cannot be attached as its
child. The member surfaces as a sibling (or top-level entry) instead of nesting under its
container.

**Consequence**: incorrect `documentSymbol` outlines for legal grammar shapes — a silent
wrong-answer, not a crash, and one the §6 test plan would not catch (its nesting test,
"hierarchical `document_symbols` nesting by containment," will naturally be written with
name-first constructs where the two orderings coincide).

**Fix**: run the nesting pass over symbols sorted by `(range_start, -range_end)` (children
render in that order too, which is still document order of the declaration ranges); add a
test with a name-anchor-after-members grammar. `SymbolTable.symbols` can stay
name-start-ordered for the lookup helpers.

## design-3 — §4.1 vs §4.2: `extract` consumes `classify`'s private `_GrammarTables`, contradicting the design's own layering rationale

**Quote (§4.1)**: the match predicate moves to `lsp_config` "because `symbols.py` and
`classify.py` now both need it and neither should reach into the other's privates."
**Quote (§4.2/§4.6)**: `extract(tree, tables, resolved_config, text)`; "`analyze()` on the
success path runs `symbols.extract(...)` (reusing `self._tables` ...)".

**What's wrong**: `self._tables` is `classify._GrammarTables` (private class,
`classify.py:63-68`), and the extraction walk additionally needs kind-name→rule resolution
(today `classify._rule_for_node`, `classify.py:162-173`, also private) to key
`def_matchers`/`ref_matchers`/`namespace_rules` by rule name, obtain node-child rule names
for `match_applies`, and check `is_trivia_rule`. So `symbols.py` as designed reaches into
exactly the privates the design's own principle forbids — the same coupling the predicate
move was justified as avoiding — and the design never says which surface becomes shared.

**Consequence**: the implementer must either violate the design's stated layering rule
(cross-module `_`-private usage, which the design elsewhere treats as disqualifying) or
improvise an undesigned refactor (publicize `_GrammarTables`/`_rule_for_node`, or duplicate
the kind→rule map in `symbols.py`). Either way the module boundary this round establishes —
new public surface per §3 ("out-of-tree consumers may construct `AnalysisEngine`s") — gets
decided by accident rather than by the design.

**Fix**: one sentence deciding it — e.g. "`_GrammarTables`/`_rule_for_node` are promoted to
public (`GrammarTables`, `rule_for_node`) as the shared rule-resolution surface for
`classify` and `symbols`", or have `extract` take an explicit kind→rule mapping.

## design-4 — §2.6/§4.5: rename's WorkspaceEdit is unversioned, leaving the client-side race the section's own rationale calls a corruption bug

**Quote (§2.6)**: "stale offsets applied to current text is a corruption bug, not a
degraded mode." **Quote (§4.5)**: "a small `rename_edits(...)` helper renders the final
`WorkspaceEdit` (one `TextEdit` per occurrence ...)".

**What's wrong**: the stale-analysis refusal and verify-reparse guard cover *server-side*
staleness only. The rename handler awaits the worker twice (analysis via
`_ensure_analyzed`, then the in-memory verify-reparse — both `run_in_executor` awaits, per
§4.6); a `didChange` can be processed on the loop between those awaits and the response.
A plain `WorkspaceEdit.changes` payload carries no version, so the client applies the
version-N offsets to version-N+1 text — precisely the corruption §2.6 exists to prevent.
LSP's mechanism for this is `WorkspaceEdit.documentChanges` with
`OptionalVersionedTextDocumentIdentifier`: a conforming client refuses a stale-versioned
edit.

**Consequence**: a rename racing a keystroke can garble the document, and the design's
rename-safety story (its most safety-argued section) is incomplete against the one race it
names as the disqualifying failure mode.

**Fix**: when the client advertises `workspace.workspaceEdit.documentChanges`, return
`documentChanges` with a `TextDocumentEdit` versioned to the analyzed document version;
fall back to `changes` otherwise (the residual race then exists only for clients that
cannot express versioned edits). One line in §2.6/§4.5 plus a server test.

## design-5 — §2.1 vs §4.2: two non-equivalent statements of the hoist condition

**Quote (§2.1)**: "a symbol whose `def` statement lives in the **same rule block** that
declares `namespace` is defined into the scope enclosing the namespace node."
**Quote (§4.2)**: "when the **parent node's own rule** is a namespace rule, the symbol
goes to the scope enclosing that node's scope."

**What's wrong**: these differ when one rule has multiple blocks — which the config model
supports (`RuleBlock.is_namespace` is per-block, `lsp_config.py:102-109`; blocks for one
rule accumulate, pinned by `test_multiple_rule_blocks_accumulate`,
`test_lsp_resolve.py:134-139`) and which this design's own §6 test plan exercises
("namespace flag accumulation across multiple blocks for one rule"). With
`rule cog { def identifier: type.cog; }` and a separate `rule cog { namespace; }`,
§2.1's block-level wording says no hoist (the def's block declares no namespace); §4.2's
rule-level wording says hoist. The resolved `namespace_rules: frozenset[str]` (§4.1) can
only express the rule-level reading — block identity is erased at resolution.

**Consequence**: the load-bearing scoping rule of the round has two readings; an
implementer or spec author following §2.1 literally gets construct names trapped in their
own scope (the exact go-to-def failure §2.1 exists to prevent) whenever a spec splits def
and namespace across blocks.

**Fix**: harmonize §2.1's wording to the rule-level condition ("whose `def` is anchored in
a rule that is a namespace rule"), and note that namespace-ness is a property of the rule
(any block may declare it).
