# Dispositions — deep review, batch 6

Commit reviewed: ae90f84671cf03d4b6e2aeed244bab3df1b1d633
Base: 663b2734c2157f8f23ed5f2a9d178070c56afca0

Reviews with **no findings**: correctness (notes-deep-correctness-r6),
security (notes-deep-security-r6), efficiency (notes-deep-efficiency-r6).

---

errhandling-1:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` `_item_anchor_lines` JOIN_BEGIN branch —
  the missing-separator `RuntimeError` now names rule/position/item, parallel to the
  unsupported-Doc-type `ValueError` wrap two lines below. `item_id` is computed once at
  the top of the branch and shared by both error paths. Test
  `test_item_level_join_anchor_without_separator_raises` updated to match the contextual
  message.
- Severity assessment: A misconfigured item-level `join` with no separator previously
  produced an anonymous message, forcing on-call to read the stack trace and
  cross-reference the FormatterConfig by hand to find the offending rule/item.

errhandling-2:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` `_item_disposition_success_lines` — replaced
  `assert isinstance(item_disposition, Normal)` with an explicit `if not isinstance(...):
  raise RuntimeError(...)` that names the offending type and the rule/item, matching the
  codebase policy already followed in the `_gen_*_term_body` routing guards. Pyright still
  narrows to `Normal` after the raise. Added unit test
  `test_item_disposition_success_lines_rejects_unknown_disposition`.
- Severity assessment: Under `python -O` the stripped assert let an unknown/misrouted
  disposition fall through to the Normal branch, silently emitting `acc = r.accumulator;`
  and corrupting the generated Rust invisibly at generation time.

scope (no scope finding file present in this batch; notes-prepass-scope-r6 exists but was
not in the assigned deep-review set): n/a — no scope findings to triage.

test-1:
- Disposition: Fixed
- Action: Added `test_quantified_regex_inner_reads_span_text`
  (`tests/test_rust_unparser_generator.py`) covering a `+` regex item's `__inner` method
  (`r := foo:/[0-9]+/+;`): the fourth `__inner` term kind, previously untested.
- Severity assessment: A regression in regex-body generation reached via `_gen_inner_methods`
  (a real production path for repeated tokenised content) would have gone undetected.

test-2:
- Disposition: Fixed
- Action: Added `test_render_as_skips_before_spacing` asserting a RenderAs item with a
  configured SPACING op emits no `before_spec`. Locks the `is_normal` gate (False for both
  Omit and RenderAs).
- Severity assessment: Narrowing the gate to an Omit-only check would have wrongly re-emitted
  a `before_spec` ahead of a RenderAs substitution, undetected by the existing Omit-only test.

test-3:
- Disposition: Fixed
- Action: Added `(gsm.Disposition.SUPPRESS, gsm.ZERO_OR_MORE, False)` to the
  `test_item_routes_to_quantified_loop_predicate` parametrize list.
- Severity assessment: A predicate refactor short-circuiting on `is_multiple()` before the
  `!= SUPPRESS` check would emit dead `__inner` methods for `SUPPRESS + *`; only caught at
  Rust compile time without this case.

reuse-1:
- Disposition: Fixed
- Action: Extracted the asymmetric LABEL/LITERAL anchor lookup into a new shared method
  `FormatterConfig.get_item_anchor_config(rule_name, item, position)`
  (`fltk/unparse/fmt_config.py`); the Rust generator's `_item_anchor_config`
  (`gsm2unparser_rs.py`) is now a thin delegation. This removes the lookup logic introduced
  by this work from the Rust generator and gives both backends one canonical, tested
  definition of the before/after selector asymmetry. The pre-existing inline copies in the
  Python `UnparserGenerator` (`gsm2unparser.py:1481`/`:1525`) were left untouched — the
  design freezes that file (§2: "the existing Python UnparserGenerator … are not touched").
  Minor additive deviation from design §2.2's "FormatterConfig queries reused unchanged";
  the new query is additive and consistent with the existing `get_item_disposition`/
  `_get_spacing` shape.
- Severity assessment: Maintenance only — without the shared method the new Rust copy of the
  asymmetric lookup would drift independently from `_get_spacing`/`get_item_disposition`.

reuse-2:
- Disposition: Fixed
- Action: `_disposition_config` (`tests/test_rust_unparser_generator.py`) now delegates the
  FormatterConfig + anchor-key/AnchorConfig construction to `_anchor_op_config` and only layers
  the disposition on top, so the key format is single-sourced between the two test builders.
- Severity assessment: Test-only maintenance — the duplicated key/AnchorConfig construction
  would have drifted if the key format or constructor signature changed.

quality-1:
- Disposition: Fixed
- Action: Added `else: raise ValueError(...)` to both the RULE_START and RULE_END anchor
  loops in `_gen_rule_entry` (`gsm2unparser_rs.py`), mirroring the fail-loud guard the
  item-level `_item_anchor_lines` already has. Added tests
  `test_rule_start_anchor_rejects_unsupported_op` and `test_rule_end_anchor_rejects_unsupported_op`.
- Severity assessment: A future `OperationType` member (or a malformed programmatic config)
  reaching the rule-level loops would previously be silently dropped, emitting an unbalanced
  push/pop accumulator stack that corrupts Doc structure with no generation-time error; the
  inconsistency with the item-level guard would also mislead the next maintainer.

---

Generated `.rs` output is unchanged: every fix touches only error-path messages, a
generation-time guard, a delegation that preserves resolution, or test code. No fixture
regeneration required (confirmed: no `.rs` files in the working tree diff).

Verification: `uv run pytest tests/test_rust_unparser_generator.py` (110 passed) plus the
unparser/fmt_config slice (112 passed); `ruff check` and `pyright` clean on all three
changed files.
