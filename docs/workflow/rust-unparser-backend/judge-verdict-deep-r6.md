# Judge verdict — deep review, batch 6

Phase: deep. Base 663b2734..HEAD 87a462b (response commit `respond(deep-r6)` over reviewed commit ae90f84). Round 1.
Notes: 7 reviewer files. 3 with no findings (correctness, security, efficiency); 8 findings across errhandling (2), test (3), reuse (2), quality (1). All dispositioned **Fixed**.

## Added TODOs walk

None. The response commit adds no `TODO(slug)` comments; every disposition is Fixed. (No scope finding in the assigned set — the dispositions doc correctly records `notes-prepass-scope-r6` as out of this batch.)

## Other findings walk

### errhandling-1 — Fixed
Claim: `gsm2unparser_rs.py:523` `_item_anchor_lines` JOIN_BEGIN branch raises `RuntimeError("JOIN_BEGIN operation missing required separator")` with no rule/position/item context; consequence is on-call must read the stack trace and cross-reference FormatterConfig by hand.
Inspection at `gsm2unparser_rs.py:526-534`: `item_id` is now computed once at the top of the JOIN_BEGIN branch and shared by both error paths; the missing-separator raise reads `f"Rule {rule_name!r} {position}-anchor JOIN_BEGIN for {item_id} is missing the required separator"`, parallel to the unsupported-Doc-type wrap two lines below. Test `test_item_level_join_anchor_without_separator_raises` updated to match (`match="Rule 'r' before-anchor JOIN_BEGIN for label='foo' is missing"`), passes.
Note: reviewer flagged the rule-level analog at `:209` as pre-existing/out-of-diff; leaving its anonymous message is consistent with the finding's own scoping, not a gap.
Assessment: fix addresses the consequence at the named line. Accept.

### errhandling-2 — Fixed
Claim: `gsm2unparser_rs.py:403` `_item_disposition_success_lines` ends in `assert isinstance(item_disposition, Normal)`, which `python -O` strips; consequence is an unknown/misrouted disposition silently falls through to the Normal branch and emits `acc = r.accumulator;`, corrupting generated Rust invisibly. Codebase policy (the `_gen_*_term_body` guards) already forbids `assert` for routing invariants.
Inspection at `:418-428`: replaced with `if not isinstance(item_disposition, Normal): raise RuntimeError(...)`; message names the offending type plus rule/item. `rule_name` and `item` are method params (both used at `:429`), so the message is valid. Pyright still narrows to `Normal` for the `:429` return. New test `test_item_disposition_success_lines_rejects_unknown_disposition` passes an `object()` and asserts the raise; passes.
Assessment: survives `-O`, fails loud, matches the documented pattern. Accept.

### test-1 — Fixed
Claim: no test covers a quantified regex term's `__inner` (the 4th inner term kind, reached via `_gen_inner_methods` → `_gen_term_body` → `_gen_regex_term_body`); a regression there would go undetected.
Inspection: `test_quantified_regex_inner_reads_span_text` generates `r := foo:/[0-9]+/+;`, extracts `unparse_r__alt0__item0__inner`, asserts the label gate, `cst::RChild::Span(span)`, `span.text()?`, `add_non_trivia(fltk_unparser_core::text(text))`, and `Some(UnparseResult::new(acc, pos + 1))`. Non-vacuous, exercises the named path. Passes.
Assessment: closes the gap. Accept.

### test-2 — Fixed
Claim: `test_omit_skips_before_spacing` covers Omit but not RenderAs; the gate is `is_normal` (False for both Omit and RenderAs), so narrowing it to an Omit-only check would wrongly re-emit `before_spec` ahead of a RenderAs substitution, undetected.
Inspection: `test_render_as_skips_before_spacing` builds a RenderAs disposition carrying a SPACING op, asserts `before_spec` absent and the substitution `add_non_trivia(Doc::Nbsp)` present. Pins the shared gate at False-for-RenderAs. Passes.
Assessment: closes the gap. Accept.

### test-3 — Fixed
Claim: `test_item_routes_to_quantified_loop_predicate` covers `(SUPPRESS, ONE_OR_MORE, False)` but not `(SUPPRESS, ZERO_OR_MORE, False)`; a refactor short-circuiting on `is_multiple()` before `!= SUPPRESS` would emit dead `__inner` methods caught only at Rust compile time.
Inspection: `(gsm.Disposition.SUPPRESS, gsm.ZERO_OR_MORE, False)` added to the parametrize list. Passes.
Assessment: closes the gap. Accept.

### reuse-1 — Fixed
Claim: `_item_anchor_config` (`gsm2unparser_rs.py:447-480`) reimplements the LABEL/LITERAL before/after asymmetry already living in `_get_spacing`/`get_item_disposition` and the Python backend's two inline copies; the new copy will drift independently.
Inspection: lookup extracted to `FormatterConfig.get_item_anchor_config(rule_name, item, position)` (`fmt_config.py:356`); `_item_anchor_config` is now a one-line delegation (`:484`). This removes the duplication *this work introduced* and gives both backends one canonical, tested definition. The pre-existing inline copies in the Python `UnparserGenerator` (`gsm2unparser.py:1481`/`:1525`) were left untouched, justified by design §2 ("the existing Python UnparserGenerator … are not touched"); the disposition calls this deviation out honestly. The finding's consequence (maintenance/drift) is addressed for the in-scope new code; unifying the frozen Python file is out of lane.
Assessment: core of the finding resolved; the leftover is design-sanctioned and disclosed. Accept.

### reuse-2 — Fixed
Claim: `_disposition_config` (test helper, `:1428`) duplicates the `FormatterConfig()` + anchor-key/AnchorConfig construction that `_anchor_op_config` (`:1214`) already does; the two will diverge if the key format or constructor changes.
Inspection: `_disposition_config` now calls `_anchor_op_config(("before", LABEL, selector_value, ops))` and only layers `.disposition` on top, single-sourcing the key/AnchorConfig construction. Test-only maintenance; consuming tests (e.g. `test_render_as_skips_before_spacing`) pass through the rewritten helper.
Assessment: closes the duplication. Accept.

### quality-1 — Fixed
Claim: the new `_item_anchor_lines` has an `else: raise` for unrecognized `OperationType`, but the pre-existing `_gen_rule_entry` RULE_START/RULE_END loops silently drop anything outside their handled set; consequence is an unbalanced push/pop accumulator stack that corrupts Doc structure with no generation-time error, plus an inconsistency that misleads the next maintainer adding an enum member.
Inspection at `:217-225` (RULE_START) and `:238-243` (RULE_END): both loops now carry `else: raise ValueError("Unsupported OperationType in RULE_{START,END} anchor for rule …")`, mirroring the item-level guard. Tests `test_rule_start_anchor_rejects_unsupported_op` and `test_rule_end_anchor_rejects_unsupported_op` assert the raise; pass.
Assessment: fail-loud parity restored at the named loops. Accept.

## Disputed items

None.

## Approved

8 findings: all Fixed and verified — errhandling-1, errhandling-2 (message/raise inspected in source), test-1/test-2/test-3 (new non-vacuous tests), reuse-1/reuse-2 (delegation confirmed), quality-1 (both loop guards present with tests). `uv run pytest tests/test_rust_unparser_generator.py` → 110 passed (includes the six new/changed tests). Generated `.rs` unchanged (no fixture regen needed — fixes touch only error messages, a generation-time guard, a delegation that preserves resolution, and test code).

---

## Verdict: APPROVED

Every disposition is Fixed and each fix addresses its finding's consequence at the named location; verified by source inspection and a green generator suite. No TODOs deferred, no Won't-Do rationales to weigh, nothing disputed.
