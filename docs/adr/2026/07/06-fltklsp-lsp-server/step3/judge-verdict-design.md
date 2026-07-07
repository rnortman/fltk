# Judge verdict — step3 design review

Phase: design (doc phase — no TODO walk). Doc: `docs/adr/2026/07/06-fltklsp-lsp-server/step3/design.md` (revised in place). Round 1.
Notes: `notes-design-design-reviewer.md` — 5 findings, all dispositioned Fixed.
Ground truth: the design doc itself + code at HEAD; advisory docs directional only per the user ("NO DECISIONS HAVE BEEN MADE").

## Findings walk

### design-1 — Fixed
Claim: §6's dogfood bullet activated "existing def/ref/namespace statements" in `fltklsp.fltklsp` that do not exist; consequence: the test is unimplementable as specified, forcing either a dropped end-to-end check or an undesigned semantic change to a committed public example file.
Verification: `fltk/lsp/fltklsp.fltklsp` contains only `scope` statements (the sole grep hit for "namespace" is `rule namespace_stmt { scope "namespace": keyword; }` — a scope paint of the keyword, not a namespace statement). Finding is factual.
Fix in doc: §6 `test_dogfood.py` bullet rewritten to the finding's option (b) — committed example stays untouched, test loads a purpose-built test-local spec against the real `fltklsp.fltkg` grammar, and the `.fltklsp`-language symbol-vocabulary question (e.g. whether repeated `rule X {}` blocks each "define" X) is explicitly parked as its own future design decision rather than a test-time improvisation.
Assessment: fix addresses the consequence exactly; the deferred question is genuinely design-cycle work, correctly not decided here. Accept.

### design-2 — Fixed
Claim: §4.5's containment stack over `name_start`-ordered symbols computes wrong nesting for trailing-name shapes; consequence: silent wrong `documentSymbol` outlines that the original test plan would not catch.
Verification: correct — a containment stack requires range-start order over laminar ranges; `name_start` order breaks when a container's def anchor follows nested member defs.
Fix in doc: §4.5 now specifies the nesting pass sorts by `(range_start, -range_end)` with the trailing-name counterexample recorded inline (`outer := "{" , member* , "}" , "as" , name:ident`); `(range_start, -range_end)` is the correct sort for laminar ranges (containers precede contained on shared starts). `SymbolTable.symbols` stays name-start-ordered for lookup helpers (§4.2), per the finding's fix. §6 `test_features.py` bullet gains the name-anchor-after-members nesting test.
Assessment: fix is technically correct and the previously-blind test gap is now explicitly covered. Accept.

### design-3 — Fixed
Claim: `extract` consumed `classify`'s privates (`_GrammarTables`, `_rule_for_node`) while §4.1's own rationale forbids cross-module private reach; consequence: the new public module boundary (§3 declares out-of-tree consumers) gets decided by implementer accident.
Verification: both names are `_`-private (`classify.py:64`, `classify.py:162`), and `engine.py:86` already receives the private `_GrammarTables` type via `classify.build_grammar_tables(...)` — the disposition's "promotion ratifies de-facto usage" claim is accurate.
Fix in doc: §4.1 gains the decision bullet — `_GrammarTables`/`_rule_for_node` promoted to public `GrammarTables`/`rule_for_node`; `symbols.extract`'s `tables` parameter is that type; extraction's three uses (matcher-lookup keying, node-child rule names for `match_applies`, `is_trivia_rule`) enumerated. §3 file-layout row for `classify.py` records the promotion.
Assessment: the one-sentence decision the finding asked for is present and consistent with the layering rationale; pure private→public rename, no behavior change, no annotation churn on existing generated surfaces. Accept.

### design-4 — Fixed
Claim: rename's `WorkspaceEdit` was unversioned, leaving the client-side race (`didChange` landing between the handler's two worker awaits) that §2.6's own rationale names as a corruption bug; fix is LSP's versioned `documentChanges`.
Verification: the handler pattern in `server.py` awaits the worker via `run_in_executor`, so loop interleaving is real; `_GoodAnalysis.version` exists (`server.py:95`) to supply the analyzed version; `OptionalVersionedTextDocumentIdentifier` in a `TextDocumentEdit` is the correct LSP mechanism.
Fix in doc: §2.6 third bullet — versioned `documentChanges` when the client advertises `workspace.workspaceEdit.documentChanges` (captured at initialize), plain `changes` fallback with the residual race explicitly confined to capability-less clients. Propagated to §4.5 (`rename_edits` packaging), §4.6 (handler + capability capture), §5 (rename-racing-a-keystroke edge case), §6 (`test_server.py` asserts both payload shapes).
Assessment: fix closes the race for conforming clients and honestly documents the unclosable residual; test plan covers both shapes. Accept.

### design-5 — Fixed
Claim: §2.1 (block-level) and §4.2 (rule-level) stated non-equivalent hoist conditions, diverging on split-block specs; consequence: the round's load-bearing scoping rule had two readings, one of which reproduces the go-to-def failure §2.1 exists to prevent.
Verification: `RuleBlock.is_namespace` is per-block (`lsp_config.py:102-109`) and multi-block accumulation is legal and pinned (`test_multiple_rule_blocks_accumulate`), so the divergence was real; the resolved `namespace_rules: frozenset[str]` can only express the rule-level reading.
Fix in doc: §2.1 harmonized to "a symbol whose `def` is anchored in a rule that is a namespace rule", with the explicit note that namespace-ness is a property of the rule, the split-block example hoisting identically, and block identity deliberately erased at resolution. §4.2's extraction rule ("parent node's own rule is a namespace rule") now agrees.
Assessment: the two statements are now equivalent and both match what the resolved representation can express. Accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified. No Won't-Do, no TODO dispositions.

---

## Verdict: APPROVED

All five fixes verified present in the revised design and factually sound against code at HEAD.
