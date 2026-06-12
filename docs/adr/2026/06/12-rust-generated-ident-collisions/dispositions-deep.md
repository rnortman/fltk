# Dispositions: deep review — rust-generated-ident-collisions

Style: concise, precise, no padding. HEAD at end of this round: 9e621d9.

---

## reuse-1

Finding: Three inline `f"Py{child_cls}"` / `f"Py{class_name}"` emission sites (gsm2tree_rs.py:727, :757, :2186) left un-converted after `py_handle_name` was introduced as single source of truth.

Disposition: Fixed (9e621d9 — same commit as quality-1)
Action: `fltk/fegen/gsm2tree_rs.py:727,757,2186` — replaced with `self.py_handle_name(child_cls)` / `self.py_handle_name(class_name)`.
Severity assessment: Future renaming of the handle prefix required edits in four places; three of them silently diverge until the drift test fires post-change.

---

## reuse-2

Finding: `_make_two_rule_grammar` contained an inner `_make_rule` duplicating the body of `_make_single_rule_grammar`; the two families would silently drift on any future change to the canonical minimal-rule shape.

Disposition: Fixed (0196f06)
Action: `tests/test_gsm2tree_rs.py:1619–1629` — `_make_single_rule_grammar` extended with `labeled: bool = True`; `_make_two_rule_grammar` now delegates to it, inner `_make_rule` eliminated.
Severity assessment: Duplicate maintenance surface; any shape change to the canonical rule structure required two independent edits.

---

## errhandling-1

Finding: `EqWorklistItem` missing from `_RESERVED_CLASS_NAMES`; rule named `eq_worklist_item` with node-typed children produces duplicate-definition Rust E0428 with no generation-time diagnostic.

Disposition: Fixed (0196f06)
Action: `fltk/fegen/gsm2tree_rs.py:44` — added `"EqWorklistItem": "the generated EqWorklistItem eq-worklist enum"`; `tests/test_gsm2tree_rs.py:1573` — added `("eq_worklist_item", "EqWorklistItem", "EqWorklistItem")` to the parametrize list.
Severity assessment: Silent bad output; `cargo build` fails with opaque E0428; the exact failure mode this entire change exists to convert into a generation-time ValueError.

---

## errhandling-2

Finding: `model = self._py_gen.rule_models.get(rule.name)` / `if model is not None and model.labels` — the `is not None` branch is dead today (CstGenerator always populates every rule), but creates a false-negative risk if `rule_models` becomes sparse in a future refactor.

Disposition: Fixed (0196f06)
Action: `fltk/fegen/gsm2tree_rs.py:143–144` — direct indexing `rule_models[rule.name]` (raises KeyError on invariant violation rather than silently skipping); guard simplified to `if model.labels:`.
Severity assessment: No missed detection today; under a future sparse-models refactor, label-enum collisions go undetected until `cargo build` fails.

---

## quality-1

Finding: Same as reuse-1 — three inline `f"Py{...}"` sites not converted to `py_handle_name`.

Disposition: Fixed (0196f06)
Action: Same as reuse-1.
Severity assessment: Same as reuse-1.

---

## quality-2

Finding: Drift-guard test (`test_prediction_vs_output_consistency`) accessed `gen._py_gen.class_name_for_rule_node(...)`, `gen._py_gen.rule_models.get(...)`, and `RustCstGenerator._label_enum_rust_name(cn)` — private implementation details. Refactoring the internal delegation structure would silently break the primary drift guard.

Disposition: Fixed (0196f06)
Action: `fltk/fegen/gsm2tree_rs.py:621–643` — exposed `label_enum_name(class_name)` public static (single source of truth for `{CN}Label`, analogous to `child_enum_name`/`py_handle_name`); added `class_name_for_rule(rule_name)` and `rule_has_labels(rule_name)` public instance methods delegating into `_py_gen`. `_label_enum_rust_name` made a thin alias for `label_enum_name`. `tests/test_gsm2tree_rs.py:1785–1812` — test rewritten using the new public API only.
Severity assessment: Internal delegation refactor would silently break the drift guard; the guard is the primary protection against `py_handle_name` divergence.

---

## test-1

Finding: `test_prediction_vs_output_consistency` used inline `f"Py{cn}"` to predict the handle identifier instead of `RustCstGenerator.py_handle_name(cn)`, making the drift guard hollow for the handle-name family.

Disposition: Fixed (0196f06)
Action: `tests/test_gsm2tree_rs.py:1799` — replaced `py_handle = f"Py{cn}"` with `py_handle = RustCstGenerator.py_handle_name(cn)`.
Severity assessment: A rename of `py_handle_name`'s body would leave the drift test passing while the emitter diverged; the formula drift protection the design required was hollow.

---

## test-2

Finding: Collision error tests checked only that the colliding identifier and rule names appeared in the error text; family-description strings ("node struct", "label enum", "Python handle struct") and the "rename" action hint were untested.

Disposition: Fixed (0196f06)
Action: `tests/test_gsm2tree_rs.py:1641–1663` — added assertions for `"child value enum"`, `"node struct"`, `"rename"` in the foo/foo_child test; `"label enum"` in the foo/foo_label test; `"Python handle struct"` in the foo/py_foo test.
Severity assessment: Error message quality regressions (swapped family descriptions, missing action hint) were uncaught; actionability guarantee was untested.

---

## test-3

Finding: Design edge case "three or more claimants on one identifier: all listed in the message" had no test; a truncation bug (e.g. `claimants[:2]`) would go undetected.

Disposition: Fixed (0196f06)
Action: `tests/test_gsm2tree_rs.py` — added `test_three_way_collision_all_claimants_reported`: grammar with `foo_bar`, `foo__bar`, `foo___bar` (all CN `FooBar`) asserts all three rule names appear in the error.
Severity assessment: Truncation of claimant lists in multi-way collisions would be uncaught.

---

## test-4

Finding: Trivia tests covered only CN-level collision (`trivia` + auto-added `_trivia` → CN `Trivia`); no test covered a user rule colliding on a derived identifier of `_trivia` (handle, child enum), leaving the auto-annotation logic untested for those families.

Disposition: Fixed (0196f06)
Action: `tests/test_gsm2tree_rs.py` — added `test_trivia_child_rule_collides_with_auto_trivia_child_enum`: single rule `trivia_child` (no explicit `_trivia`) asserts error names `TriviaChild`, `trivia_child`, and the auto-generated annotation.
Severity assessment: A bug annotating only CN-family claims as auto-generated would not be detected.

---

## correctness-1

Finding: `EqWorklistItem` missing from `_RESERVED_CLASS_NAMES` (same as errhandling-1).

Disposition: Fixed (0196f06) — see errhandling-1.
Action: See errhandling-1.
Severity assessment: See errhandling-1.

---

## correctness-2

Finding: Module-level invariant guard used `assert`, which is compiled out under `python -O` / `PYTHONOPTIMIZE`. The cross-rule check's correctness argument depends on this invariant holding at all times.

Disposition: Fixed (9e621d9)
Action: `fltk/fegen/gsm2tree_rs.py:56–65` — replaced `assert all(...)` with explicit `if _bad_reserved: raise RuntimeError(...)`. Invariant now survives `-O`.
Severity assessment: Under optimized Python, a future reserved name violating the invariant (e.g. `"PySpan"`) would import cleanly, allowing a colliding rule to be accepted and producing duplicate-identifier Rust E0428 with no generation-time diagnostic.

---

## correctness-3

Finding: Pre-existing (not introduced by this diff): underscore-only rule names (`_`, `__`) pass `_IDENTIFIER_RE` but `snake_to_upper_camel` collapses them to CN `""`, producing `pub struct  {` (Rust syntax error) with no generation-time diagnostic.

Disposition: TODO(empty-cn-underscore-rule)
Action: `fltk/fegen/gsm2tree_rs.py:21–25` — TODO comment at `_IDENTIFIER_RE` definition; `TODO.md` — new entry `empty-cn-underscore-rule` with slug, description, and location.
Severity assessment: Pre-existing gap; the same class of silent-bad-output problem this change targets. Fix requires either tightening the regex or adding a post-CN empty-string check in the validation loop.
