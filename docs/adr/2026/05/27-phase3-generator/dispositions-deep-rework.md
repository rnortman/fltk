Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Rework round. Disputed items only.

---

## errhandling-4

- Disposition: Fixed
- Action: Replaced `TODO(errhandling-count-context)` comment and generic expect message with `f'        Ok(found.expect("invariant: {class_name}.child_{label}: count==1 but found==None; logic error"))'` in `_per_label_methods`. Each generated `child_{label}` method now embeds its class and label in the panic message. `gsm2tree_rs.py:382`.
- Severity assessment: The invariant is provably unreachable by construction, so the diagnostic value is purely for future debugging of logic errors in the generator. The fix was mechanical string interpolation with no design decision required; deferral was incorrect per Q2 rubric.

---

## quality-3

- Disposition: Fixed
- Action: Extracted `_rule_info() -> list[tuple[str, list[str]]]` at `gsm2tree_rs.py:74-100`. Both `generate()` and `_register_classes_fn()` now call `_rule_info()` instead of each running their own loop over `self.grammar.rules`. The `TODO(refactor-rule-info-helper)` comment is removed. No behavior change; same error messages now say `_rule_info()` rather than the caller name.
- Severity assessment: Eliminated the duplicate derivation that could silently diverge if one loop gained a conditional skip. The extraction was mechanical within the same class; deferral was incorrect per Q2 rubric.

---

## efficiency-1

- Disposition: TODO(perf-label-identity-comparison)
- Action: Added `TODO(perf-label-identity-comparison)` comment at `gsm2tree_rs.py:334-337` in `_per_label_methods`, immediately before the `lines.extend([...])` block that emits the `tup.get_item(0)?.eq(&label_obj)?` O(n) scan pattern. Added corresponding entry in `TODO.md`. The TODO is placed in the Python generator (the authoritative location for this template choice) rather than in the generated `.rs` file (which is regenerated).
- Severity assessment: O(n) linear scan per label access; not a regression from Phase 2 template. No measured bottleneck. Defer until profiling confirms cost.

---

## Missing TODO.md entries (all four accepted TODOs)

- Disposition: Fixed
- Action: Added entries to `TODO.md` for all accepted deferred TODOs:
  - `extract-rule-name-to-class-name`: four-site duplication of underscore-to-CamelCase transform.
  - `test-class-is-type-body`: weak `isinstance(cls, type)` assertion in AC-7 test.
  - `perf-label-identity-comparison`: O(n) label-accessor scan pattern.
  - `errhandling-count-context` and `refactor-rule-info-helper` are not added — both findings are now Fixed, so no deferred TODO remains in code or TODO.md for them.
- Severity assessment: Per project convention (CLAUDE.md), every `TODO(slug)` comment requires a matching TODO.md entry. Three deferred TODOs now have entries; two previously-deferred TODOs are Fixed and require no entry.
